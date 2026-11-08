import html
import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx
from mistralai import agents
from pypdf import PdfReader
from pydantic import Field, ValidationError

from models import SyntheseVeille, VeillePortefeuille, VeilleScpi

DATA_DIR = Path(__file__).with_name("data")
SOURCES_FILE = DATA_DIR / "sources.json"
USER_AGENT = "veille-agent/1.0 (projet educatif)"

RESULT_A_RE = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)


def _strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _unwrap_ddg(href: str) -> str:
    if href.startswith("//duckduckgo.com/l/") or "uddg=" in href:
        parsed = urlparse(href if "://" in href else "https:" + href)
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return target[0]
    return href


def _parse_ddg(page: str) -> list[dict]:
    titles = RESULT_A_RE.findall(page)
    snippets = SNIPPET_RE.findall(page)
    results = []
    for i, (href, title_html) in enumerate(titles):
        snippet = _strip_html(snippets[i]) if i < len(snippets) else ""
        results.append(
            {"title": _strip_html(title_html), "url": _unwrap_ddg(href), "snippet": snippet}
        )
    return results


def _parse_arxiv(xml_text: str) -> list[dict]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", ns):
        title = _strip_html(entry.findtext("atom:title", default="", namespaces=ns))
        summary = _strip_html(entry.findtext("atom:summary", default="", namespaces=ns))
        entries.append(
            {
                "title": title,
                "url": entry.findtext("atom:id", default="", namespaces=ns),
                "published": entry.findtext("atom:published", default="", namespaces=ns)[:10],
                "snippet": summary[:300],
            }
        )
    return entries


def _load_sources() -> list[dict]:
    if SOURCES_FILE.exists():
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return []


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    return re.sub(r"\s+", " ", text).strip()


@agents.tool
def web_search(
    query: Annotated[str, Field(description="Requête de recherche en langage naturel, ex. 'agents LLM 2026 tendances'")],
    max_results: Annotated[int, Field(description="Nombre maximum de résultats renvoyés")] = 6,
) -> list[dict]:
    """Recherche sur le web et renvoie pour chaque résultat un titre, une URL et un extrait."""
    url = "https://html.duckduckgo.com/html/?q=" + quote_plus(query)
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        raise agents.ToolError(f"La recherche web a échoué ({type(exc).__name__}). Réessaie avec une autre formulation.")
    if resp.status_code != 200:
        raise agents.ToolError(f"Le moteur de recherche a répondu HTTP {resp.status_code}.")
    results = _parse_ddg(resp.text)[:max_results]
    if not results:
        raise agents.ToolError(f"Aucun résultat pour « {query} ». Essaie une autre formulation.")
    return results


@agents.tool
def search_arxiv(
    query: Annotated[str, Field(description="Sujet scientifique, ex. 'LLM multi-agent evaluation'")],
    max_results: Annotated[int, Field(description="Nombre maximum de preprints renvoyés")] = 5,
) -> list[dict]:
    """Recherche les preprints les plus récents sur arXiv (veille scientifique et technique)."""
    api = (
        "https://export.arxiv.org/api/query?search_query=all:"
        + quote_plus(query)
        + f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(api)
    except httpx.HTTPError as exc:
        raise agents.ToolError(f"La recherche arXiv a échoué ({type(exc).__name__}).")
    if resp.status_code != 200:
        raise agents.ToolError(f"arXiv a répondu HTTP {resp.status_code}.")
    entries = _parse_arxiv(resp.text)
    if not entries:
        raise agents.ToolError(f"Aucun preprint arXiv pour « {query} ».")
    return entries


@agents.tool
def fetch_url(
    url: Annotated[str, Field(description="URL http(s) complète de la page à lire")],
    max_chars: Annotated[int, Field(description="Nombre maximum de caractères de texte renvoyés")] = 6000,
) -> dict:
    """Télécharge une page web et renvoie son titre et son texte brut (tronqué)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise agents.ToolError(f"URL invalide : {url!r}. Donne une URL http(s) complète.")
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
    except httpx.HTTPError as exc:
        raise agents.ToolError(f"Téléchargement de {url} échoué : {type(exc).__name__}.")
    if resp.status_code != 200:
        raise agents.ToolError(f"{url} a répondu HTTP {resp.status_code}.")
    ctype = resp.headers.get("content-type", "")
    if "pdf" in ctype:
        title = url
        text = _extract_pdf_text(resp.content)
    elif any(t in ctype for t in ("html", "text", "xml", "json")):
        title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", resp.text)
        title = _strip_html(title_m.group(1)) if title_m else url
        text = _strip_html(resp.text) if "html" in ctype else resp.text.strip()
    else:
        raise agents.ToolError(f"Contenu non supporté ({ctype or 'inconnu'}) pour {url}.")
    return {"url": str(resp.url), "title": title, "text": text[:max_chars]}


@agents.tool
def save_source(
    url: Annotated[str, Field(description="URL de la source lue")],
    title: Annotated[str, Field(description="Titre de la source")],
    key_points: Annotated[list[str], Field(description="2 à 5 points clés retenus de cette source")],
    reliability: Annotated[Literal["primaire", "secondaire", "faible"], Field(description="Fiabilité estimée de la source")],
) -> str:
    """Enregistre une source dans le registre local et renvoie son identifiant de citation [Sn]."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sources = _load_sources()
    source_id = f"S{len(sources) + 1}"
    sources.append(
        {"id": source_id, "url": url, "title": title, "key_points": key_points, "reliability": reliability}
    )
    SOURCES_FILE.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    return source_id


def _cited_ids_in_json(obj) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, str):
        found.update(re.findall(r"S\d+", obj))
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found |= _cited_ids_in_json(key) | _cited_ids_in_json(value)
    elif isinstance(obj, list):
        for item in obj:
            found |= _cited_ids_in_json(item)
    return found


def _render_synthese(synthese_json: str) -> str:
    for model in (VeillePortefeuille, SyntheseVeille, VeilleScpi):
        try:
            return model.model_validate_json(synthese_json).render_markdown()
        except ValidationError:
            continue
    pretty = json.dumps(json.loads(synthese_json), indent=2, ensure_ascii=False)
    return f"```json\n{pretty}\n```\n"


@agents.tool
def save_synthesis(
    topic: Annotated[str, Field(description="Sujet de la veille, utilisé pour nommer le fichier")],
    synthese_json: Annotated[str, Field(description="Synthèse finale en JSON conforme au schéma de sortie demandé par l'agent")],
) -> str:
    """Enregistre la synthèse finale (JSON structuré) et la rend en Markdown. Refusée si elle cite des [Sn] non enregistrés ou aucune source."""
    try:
        data = json.loads(synthese_json)
    except json.JSONDecodeError as exc:
        raise agents.ToolError(f"JSON invalide : {exc}")
    cited = _cited_ids_in_json(data)
    if not cited:
        raise agents.ToolError("La synthèse ne cite aucune source [Sn]. Enregistre d'abord les sources avec save_source.")
    known = {s["id"] for s in _load_sources()}
    unknown = sorted(cited - known)
    if unknown:
        raise agents.ToolError(
            f"Citations inconnues : {', '.join(unknown)}. Enregistre ces sources avec save_source avant de soumettre la synthèse."
        )
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:60] or "synthese"
    out_dir = DATA_DIR / "syntheses"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.md"
    path.write_text(_render_synthese(synthese_json), encoding="utf-8")
    return str(path)


@agents.tool
def find_source(
    url: Annotated[str, Field(description="URL exacte à rechercher dans le registre des sources")],
) -> str:
    """Renvoie l'identifiant [Sn] d'une source déjà enregistrée pour cette URL, ou 'aucune' si elle n'est pas enregistrée."""
    for s in _load_sources():
        if s["url"] == url:
            return s["id"]
    return "aucune"


@agents.tool
def list_saved_sources() -> list[dict]:
    """Liste les sources déjà enregistrées (id, titre, url, fiabilité) pour éviter les doublons entre veilles."""
    return [
        {"id": s["id"], "titre": s["title"], "url": s["url"], "fiabilite": s["reliability"]}
        for s in _load_sources()
    ]