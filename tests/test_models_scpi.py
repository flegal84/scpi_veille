import pytest
from pydantic import ValidationError

from models import VeilleScpi


def veille_scpi_valide(**overrides) -> dict:
    data = {
        "scpi": "Pierval Santé",
        "societe_gestion": "Euryale Asset Management",
        "date_veille": "2026-11-08",
        "periode": "T3 2026",
        "indicateurs": {
            "prix_part": {"valeur": "204 €", "date_valeur": "30/09/2026", "sources": ["S1"]},
            "valeur_realisation": {"valeur": "182,56 €", "date_valeur": "31/12/2025", "sources": ["S1"]},
            "valeur_reconstitution": {"valeur": "199,21 €", "date_valeur": "30/06/2026", "sources": ["S1"]},
            "parts_attente_vente": {"valeur": "712 725 parts (4,40 % de la capitalisation)", "date_valeur": "30/09/2026", "sources": ["S1", "S2"]},
        },
        "medias": [
            {"titre": "Pierval Santé publie son bulletin T3 2026", "url": "https://www.pierrepapier.fr/x", "date": "30/10/2026", "resume": "Le backlog progresse."}
        ],
        "evolution": ["Parts en attente en hausse vs T2 2026."],
        "incertitudes": ["Valeur de réalisation annuelle 2026 non encore publiée."],
        "veille_insuffisante": False,
        "sources": [
            {"id": "S1", "titre": "Bulletin T3 2026 (Euryale AM)", "url": "https://www.euryale-am.fr/bt.pdf", "fiabilite": "primaire"},
            {"id": "S2", "titre": "Article média", "url": "https://www.pierrepapier.fr/x", "fiabilite": "secondaire"},
        ],
    }
    data.update(overrides)
    return data


def test_veille_scpi_valide():
    v = VeilleScpi.model_validate(veille_scpi_valide())
    assert v.indicateurs.prix_part.valeur == "204 €"
    assert v.cited_source_ids() == {"S1", "S2"}


def test_indicateur_citant_source_non_listee_rejete():
    data = veille_scpi_valide()
    data["indicateurs"]["prix_part"]["sources"] = ["S9"]
    with pytest.raises(ValidationError, match="absentes du champ 'sources'"):
        VeilleScpi.model_validate(data)


def test_id_source_invalide_rejete():
    data = veille_scpi_valide()
    data["indicateurs"]["valeur_reconstitution"]["sources"] = ["X1"]
    with pytest.raises(ValidationError):
        VeilleScpi.model_validate(data)


def test_valeur_null_acceptee():
    data = veille_scpi_valide()
    data["indicateurs"]["valeur_retrait"] = {"valeur": None, "date_valeur": None, "sources": []}
    v = VeilleScpi.model_validate(data)
    assert v.indicateurs.valeur_retrait.valeur is None


def test_render_markdown():
    md = VeilleScpi.model_validate(veille_scpi_valide()).render_markdown()
    assert md.startswith("# Veille SCPI — Pierval Santé")
    assert "**Prix de la part** : 204 € (au 30/09/2026) [S1]" in md
    assert "**Parts en attente de vente/retrait**" in md
    assert "[S1][S2]" in md
    assert "## Actualité média" in md
    assert "pas un conseil en investissement" in md