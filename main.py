import asyncio
import os
import sys
from pathlib import Path

from mistralai import agents

from models import SyntheseVeille
from tools import fetch_url, save_source, save_synthesis, search_arxiv, web_search

SKILLS_DIR = Path(__file__).with_name("skills")

INSTRUCTIONS = (
    "Tu es un analyste de veille. Pour toute demande de veille, d'état de l'art ou de synthèse "
    "d'actualité : charge le skill 'veille-synthese' avec l'outil skill.read et applique-le à la lettre. "
    "Cite chaque affirmation importante par [Sn], où Sn est l'identifiant renvoyé par save_source. "
    "N'invente jamais une source, une statistique ou une date. Si les sources sont insuffisantes ou "
    "contradictoires, dis-le explicitement (champs divergences / incertitudes / veille_insuffisante). "
    "Ta réponse finale est l'objet JSON du schéma de sortie ; passe ce même JSON à save_synthesis."
)


def _environment() -> agents.Sandbox:
    choice = os.environ.get("VEILLE_SANDBOX", "bashkit").lower()
    if choice == "mistral":
        return agents.MistralSandbox()
    if choice == "none":
        return agents.NoSandbox()
    return agents.BashkitSandbox()


agent = agents.Agent(
    model=os.environ.get("VEILLE_MODEL", "mistral-large-4"),
    name="veille-synthese",
    description="Agent de veille produisant des synthèses sourcées avec citations [Sn].",
    instructions=INSTRUCTIONS,
    tools=[web_search, search_arxiv, fetch_url, save_source, save_synthesis],
    skills=[agents.LocalSkillBundle.from_directory(SKILLS_DIR / "veille-synthese")],
    environment=_environment(),
    max_iterations=30,
    tool_errors="show",
    output_type=SyntheseVeille,
)


async def main() -> None:
    prompt = " ".join(sys.argv[1:]) or (
        "Fais une veille sur les agents LLM : quelles sont les principales tendances récentes ?"
    )
    state = await agent.run(prompt)
    if isinstance(state, agents.Completed):
        if isinstance(state.output, SyntheseVeille):
            print(state.output.model_dump_json(indent=2, ensure_ascii=False))
        elif isinstance(state.output, agents.InvalidOutput):
            print("Sortie non conforme au schéma :", state.output.error)
            print(state.text)
        print("\nOutils appelés :", [call.name for call in state.tool_calls])
    else:
        print("État du tour :", state)


if __name__ == "__main__":
    asyncio.run(main())