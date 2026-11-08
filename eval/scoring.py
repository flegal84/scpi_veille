from models import SyntheseVeille


def score_case(case: dict, synthese: SyntheseVeille | None, known_source_ids: set[str]) -> dict:
    base = {
        "citations_min": False,
        "citations_connues": False,
        "sources_listees": False,
        "incertitudes": False,
    }
    if case.get("expect_insufficient"):
        base["veille_insuffisante_signalee"] = False
    if synthese is None:
        return {
            "case_id": case["id"],
            "checks": base,
            "score": 0.0,
            "citations": [],
            "citations_inconnues": [],
        }

    citations = synthese.cited_source_ids()
    unknown = sorted(citations - known_source_ids)
    incertitude = bool(synthese.incertitudes or synthese.divergences) or synthese.veille_insuffisante
    checks = {
        "citations_min": len(citations) >= case.get("min_citations", 0),
        "citations_connues": not unknown,
        "sources_listees": len(synthese.sources) > 0,
        "incertitudes": (not case.get("require_uncertainty")) or incertitude,
    }
    if case.get("expect_insufficient"):
        checks["veille_insuffisante_signalee"] = synthese.veille_insuffisante
    return {
        "case_id": case["id"],
        "checks": checks,
        "score": sum(checks.values()) / len(checks),
        "citations": sorted(citations),
        "citations_inconnues": unknown,
    }