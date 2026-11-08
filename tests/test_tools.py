import json
from pathlib import Path

import pytest
from mistralai import agents

import tools

FIXTURES = Path(__file__).parent / "fixtures"


def _use_tmp_data(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tools, "SOURCES_FILE", tmp_path / "sources.json")


def test_strip_html_supprime_scripts_et_balises():
    raw = "<html><head><style>body{}</style></head><body><h1>Titre</h1><script>evil()</script><p>Bonjour &amp; bienvenue</p></body></html>"
    assert tools._strip_html(raw) == "Titre Bonjour & bienvenue"


def test_parse_ddg_debalise_et_resout_les_redirections():
    page = (FIXTURES / "ddg_sample.html").read_text(encoding="utf-8")
    results = tools._parse_ddg(page)
    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/article1"
    assert results[0]["title"] == "Article Exemple Un"
    assert "agents LLM progressent" in results[0]["snippet"]
    assert results[1]["url"] == "https://direct.example.org/page2"
    assert results[1]["snippet"] == "Le RAG reste central. source fiable."


def test_parse_arxiv():
    xml = (FIXTURES / "arxiv_sample.xml").read_text(encoding="utf-8")
    entries = tools._parse_arxiv(xml)
    assert len(entries) == 2
    assert entries[0]["url"] == "http://arxiv.org/abs/2601.00001v1"
    assert entries[0]["published"] == "2026-01-05"
    assert entries[0]["title"] == "Evaluating LLM Agents: A Survey"
    assert "benchmarks" in entries[0]["snippet"]


def test_fetch_url_rejette_un_shema_invalide():
    with pytest.raises(agents.ToolError):
        tools.fetch_url("ftp://example.com/fichier")
    with pytest.raises(agents.ToolError):
        tools.fetch_url("pas-une-url")


def test_save_source_attribue_des_ids_sequentiels(tmp_path, monkeypatch):
    _use_tmp_data(tmp_path, monkeypatch)
    assert tools.save_source("https://a.example", "Source A", ["point 1"], "primaire") == "S1"
    assert tools.save_source("https://b.example", "Source B", ["point 2"], "secondaire") == "S2"
    data = json.loads((tmp_path / "sources.json").read_text(encoding="utf-8"))
    assert [s["id"] for s in data] == ["S1", "S2"]
    assert data[0]["reliability"] == "primaire"


def _synthese_json(**overrides) -> str:
    import json as _json

    from tests.test_models import synthese_valide

    return _json.dumps(synthese_valide(**overrides), ensure_ascii=False)


def test_save_synthesis_refuse_sans_citation(tmp_path, monkeypatch):
    _use_tmp_data(tmp_path, monkeypatch)
    tools.save_source("https://a.example", "Source A", ["point 1"], "primaire")
    data = json.loads(_synthese_json())
    data["points_cles"] = [{"affirmation": "Sans source.", "sources": []}]
    data["sources"] = []
    with pytest.raises(agents.ToolError, match="aucune source"):
        tools.save_synthesis("sujet", json.dumps(data, ensure_ascii=False))


def test_save_synthesis_refuse_citation_inconnue(tmp_path, monkeypatch):
    _use_tmp_data(tmp_path, monkeypatch)
    tools.save_source("https://a.example", "Source A", ["point 1"], "primaire")
    data = json.loads(_synthese_json())
    data["points_cles"][0]["sources"] = ["S1", "S9"]
    data["sources"].append({"id": "S9", "titre": "Fantôme", "url": "https://x.example", "fiabilite": "faible"})
    with pytest.raises(agents.ToolError, match="S9"):
        tools.save_synthesis("sujet", json.dumps(data, ensure_ascii=False))


def test_save_synthesis_refuse_json_invalide(tmp_path, monkeypatch):
    _use_tmp_data(tmp_path, monkeypatch)
    tools.save_source("https://a.example", "Source A", ["point 1"], "primaire")
    with pytest.raises(agents.ToolError, match="JSON invalide"):
        tools.save_synthesis("sujet", "ceci n'est pas du JSON")


def test_save_synthesis_accepte_et_rend_le_markdown(tmp_path, monkeypatch):
    _use_tmp_data(tmp_path, monkeypatch)
    tools.save_source("https://a.example", "Article A", ["point 1"], "primaire")
    tools.save_source("https://b.example", "Preprint B", ["point 2"], "secondaire")
    path = tools.save_synthesis("Veille Agents LLM", _synthese_json())
    assert Path(path).exists()
    assert "veille-agents-llm" in path
    contenu = Path(path).read_text(encoding="utf-8")
    assert "## Points clés" in contenu
    assert "[S1][S2]" in contenu
    assert "## Sources" in contenu


def test_find_source_et_list_saved_sources(tmp_path, monkeypatch):
    _use_tmp_data(tmp_path, monkeypatch)
    assert tools.find_source("https://a.example") == "aucune"
    tools.save_source("https://a.example", "Source A", ["point 1"], "primaire")
    assert tools.find_source("https://a.example") == "S1"
    assert tools.list_saved_sources() == [
        {"id": "S1", "titre": "Source A", "url": "https://a.example", "fiabilite": "primaire"}
    ]


def test_extract_pdf_text(monkeypatch):
    class FakePage:
        def __init__(self, texte):
            self.texte = texte

        def extract_text(self):
            return self.texte

    class FakeReader:
        def __init__(self, stream):
            self.pages = [FakePage("Bonjour"), FakePage("le   monde\nPDF")]

    monkeypatch.setattr(tools, "PdfReader", FakeReader)
    assert tools._extract_pdf_text(b"%PDF-fake") == "Bonjour le monde PDF"