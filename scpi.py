import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from mistralai import agents

from main import _environment
from models import VeillePortefeuille
from tools import fetch_url, find_source, list_saved_sources, save_source, save_synthesis, web_search

SKILLS_DIR = Path(__file__).with_name("skills")
DATA_DIR = Path(__file__).with_name("data")

PORTEFEUILLE = [
    "Pierval Santé",
    "Epargne Pierre",
    "Iroko Zen",
    "Transitions Europe",
    "Corum Origin",
    "Corum XL",
    "Corum Eurion",
    "Remake Live",
]

INSTRUCTIONS_SCPI = (
    "Tu es un analyste spécialisé SCPI. Pour chaque veille sur un portefeuille de SCPI, charge le skill "
    "'scpi-veille' avec skill.read et applique-le (sociétés de gestion, sources prioritaires, champs à "
    "extraire, règles). Vérifie chaque chiffre dans la source primaire (site de la société de gestion) "
    "avant de le citer [Sn]. N'invente jamais une valeur. Ta réponse finale est l'objet JSON du schéma "
    "de sortie (VeillePortefeuille) ; passe ce même JSON à save_synthesis."
)


def _prompt(scpis: list[str]) -> str:
    return (
        "Veille périodique sur mon portefeuille de SCPI : " + ", ".join(scpis) + ". "
        "Pour chaque SCPI, extrais du dernier bulletin trimestriel / rapport annuel publié par sa société "
        "de gestion : prix de la part, valeur de réalisation, valeur de reconstitution, valeur de retrait "
        "si publiée, nombre de parts en attente de retrait/vente (avec % de la capitalisation), collecte "
        "du trimestre, dividende du trimestre et taux de distribution annuel, TOF, capitalisation. "
        "Ajoute l'actualité média des 90 derniers jours par SCPI. Chaque chiffre doit porter sa date "
        "d'arrêté et sa citation [Sn]. Termine par une comparaison transversale entre les SCPI du portefeuille."
    )


scpi_agent = agents.Agent(
    model=os.environ.get("VEILLE_MODEL", "mistral-large-4"),
    name="scpi-veille-portefeuille",
    description="Veille périodique multi-SCPI (portefeuille) : prix de la part, valeurs de réalisation/reconstitution/retrait, parts en attente de vente, collecte, dividende, TOF, actualité média, comparaison transversale.",
    instructions=INSTRUCTIONS_SCPI,
    tools=[web_search, fetch_url, save_source, find_source, list_saved_sources, save_synthesis],
    skills=[
        agents.LocalSkillBundle.from_directory(SKILLS_DIR / "veille-synthese"),
        agents.LocalSkillBundle.from_directory(SKILLS_DIR / "scpi-veille"),
    ],
    environment=_environment(),
    max_iterations=40,
    tool_errors="show",
    output_type=VeillePortefeuille,
)


async def run_veille(prompt: str, topic: str) -> None:
    state = await scpi_agent.run(prompt)
    if not isinstance(state, agents.Completed):
        print("État du tour :", state)
        return
    if isinstance(state.output, VeillePortefeuille):
        veille = state.output
        hist_dir = DATA_DIR / "historique"
        hist_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = hist_dir / f"veille-portefeuille-{stamp}.json"
        path.write_text(veille.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
        print(veille.model_dump_json(indent=2, ensure_ascii=False))
        print(f"\nHistorique enregistré : {path}")
    elif isinstance(state.output, agents.InvalidOutput):
        print("Sortie non conforme au schéma :", state.output.error)
        print(state.text)
    print("Outils appelés :", [c.name for c in state.tool_calls])


async def main() -> None:
    scpis = sys.argv[1:] or PORTEFEUILLE
    await run_veille(_prompt(scpis), topic=", ".join(scpis))


if __name__ == "__main__":
    asyncio.run(main())