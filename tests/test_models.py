import pytest
from pydantic import ValidationError

from models import SyntheseVeille


def synthese_valide(**overrides) -> dict:
    data = {
        "sujet": "Tendances agents LLM",
        "date_veille": "2026-11-08",
        "veille_insuffisante": False,
        "resume_executif": ["Les agents outillés dominent", "Le RAG progresse", "L'évaluation reste difficile"],
        "points_cles": [
            {"affirmation": "Les agents appellent des outils externes.", "sources": ["S1", "S2"]},
            {"affirmation": "L'évaluation reste un point ouvert.", "sources": ["S2"]},
        ],
        "divergences": ["Certaines sources citent 2025 comme année charnière."],
        "incertitudes": ["Impact réel des agents sur la productivité non tranché."],
        "sources": [
            {"id": "S1", "titre": "Article A", "url": "https://a.example", "fiabilite": "primaire"},
            {"id": "S2", "titre": "Preprint B", "url": "https://b.example", "fiabilite": "secondaire"},
        ],
    }
    data.update(overrides)
    return data


def test_modele_valide():
    s = SyntheseVeille.model_validate(synthese_valide())
    assert s.cited_source_ids() == {"S1", "S2"}
    assert s.sources[0].id == "S1"


def test_id_source_invalide_rejete():
    data = synthese_valide()
    data["points_cles"][0]["sources"] = ["S1", "X9"]
    with pytest.raises(ValidationError):
        SyntheseVeille.model_validate(data)


def test_point_citant_source_non_listee_rejete():
    data = synthese_valide()
    data["points_cles"][0]["sources"] = ["S1", "S7"]
    with pytest.raises(ValidationError, match="absentes du champ 'sources'"):
        SyntheseVeille.model_validate(data)


def test_date_invalide_rejetee():
    with pytest.raises(ValidationError):
        SyntheseVeille.model_validate(synthese_valide(date_veille="08/11/2026"))


def test_resume_trop_long_rejete():
    with pytest.raises(ValidationError):
        SyntheseVeille.model_validate(synthese_valide(resume_executif=["a", "b", "c", "d"]))


def test_render_markdown():
    md = SyntheseVeille.model_validate(synthese_valide()).render_markdown()
    assert md.startswith("# Tendances agents LLM")
    assert "## Résumé exécutif" in md
    assert "appellent des outils externes. [S1][S2]" in md
    assert "## Incertitudes" in md
    assert "## Sources" in md
    assert "- [S1] Article A — https://a.example — primaire" in md


def test_render_markdown_veille_insuffisante():
    data = synthese_valide(veille_insuffisante=True)
    data["points_cles"] = [{"affirmation": "Peu de sources solides.", "sources": ["S1"]}]
    md = SyntheseVeille.model_validate(data).render_markdown()
    assert "Veille insuffisante" in md