"""Lance l'agent sur les cas de eval/cases.json et score les sorties structurées.

Usage : MISTRAL_API_KEY=... python eval/run_eval.py
Écrit eval/results.json. Sans clé API, seuls les tests unitaires d'éval tournent
(voir tests/test_scoring.py).
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mistralai import agents

from eval.scoring import score_case
from main import agent
from models import SyntheseVeille
from tools import _load_sources

EVAL_DIR = Path(__file__).resolve().parent


async def run_case(case: dict) -> dict:
    state = await agent.run(case["topic"])
    synthese = None
    if isinstance(state, agents.Completed) and isinstance(state.output, SyntheseVeille):
        synthese = state.output
    return score_case(case, synthese, {s["id"] for s in _load_sources()})


async def main() -> None:
    cases = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))["cases"]
    results = [await run_case(case) for case in cases]
    global_score = sum(r["score"] for r in results) / len(results)
    report = {"score_global": round(global_score, 3), "results": results}
    (EVAL_DIR / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in results:
        print(f"{r['case_id']}: {r['score']:.0%}  citations={r['citations']} inconnues={r['citations_inconnues']}")
        for name, ok in r["checks"].items():
            if not ok:
                print(f"    ÉCHEC: {name}")
    print(f"\nScore global: {global_score:.0%}")


if __name__ == "__main__":
    asyncio.run(main())