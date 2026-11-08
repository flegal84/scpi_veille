import pytest
from pydantic import ValidationError

from models import VeillePortefeuille
from tests.test_models_scpi import veille_scpi_valide


def portefeuille_valide() -> dict:
    v1 = veille_scpi_valide()
    v2 = veille_scpi_valide(scpi="Corum Origin", societe_gestion="Corum AM")
    return {
        "date_veille": "2026-11-08",
        "scpis": [v1, v2],
        "synthese": ["Pierval Santé a un backlog de 4,40 % ; Corum Origin n'en a pas."],
    }


def test_portefeuille_valide():
    p = VeillePortefeuille.model_validate(portefeuille_valide())
    assert len(p.scpis) == 2
    assert p.cited_source_ids() == {"S1", "S2"}


def test_minimum_une_scpi():
    with pytest.raises(ValidationError):
        VeillePortefeuille.model_validate({"date_veille": "2026-11-08", "scpis": []})


def test_render_markdown():
    md = VeillePortefeuille.model_validate(portefeuille_valide()).render_markdown()
    assert md.startswith("# Veille portefeuille SCPI — 2026-11-08")
    assert "# Veille SCPI — Pierval Santé" in md
    assert "# Veille SCPI — Corum Origin" in md
    assert "# Comparaison transversale" in md
    assert "pas un conseil en investissement" in md