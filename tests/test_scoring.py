from eval.scoring import score_case
from models import SyntheseVeille
from tests.test_models import synthese_valide


def _synthese(**overrides) -> SyntheseVeille:
    return SyntheseVeille.model_validate(synthese_valide(**overrides))


def test_score_parfait():
    case = {"id": "t1", "min_citations": 2, "require_uncertainty": True}
    result = score_case(case, _synthese(), {"S1", "S2"})
    assert result["score"] == 1.0
    assert result["citations"] == ["S1", "S2"]
    assert result["citations_inconnues"] == []


def test_citation_inconnue_penalise():
    case = {"id": "t2", "min_citations": 1, "require_uncertainty": False}
    result = score_case(case, _synthese(), {"S1"})
    assert result["checks"]["citations_connues"] is False
    assert result["citations_inconnues"] == ["S2"]


def test_trop_peu_de_citations():
    case = {"id": "t3", "min_citations": 3, "require_uncertainty": False}
    data = synthese_valide()
    data["points_cles"] = [{"affirmation": "Un seul point.", "sources": ["S1"]}]
    result = score_case(case, SyntheseVeille.model_validate(data), {"S1", "S2"})
    assert result["checks"]["citations_min"] is False


def test_veille_insuffisante_attendue():
    case = {"id": "t4", "min_citations": 0, "require_uncertainty": True, "expect_insufficient": True}
    data = synthese_valide(veille_insuffisante=True)
    data["points_cles"] = [{"affirmation": "Peu de sources.", "sources": ["S1"]}]
    result = score_case(case, SyntheseVeille.model_validate(data), {"S1", "S2"})
    assert result["checks"]["veille_insuffisante_signalee"] is True


def test_sortie_invalide_score_zero():
    case = {"id": "t5", "min_citations": 1, "require_uncertainty": False}
    result = score_case(case, None, set())
    assert result["score"] == 0.0