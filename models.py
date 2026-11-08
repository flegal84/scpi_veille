import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ID_RE = re.compile(r"S\d+")


def valide_ids_sources(value: list[str]) -> list[str]:
    for sid in value:
        if not ID_RE.fullmatch(sid):
            raise ValueError(f"identifiant de source invalide : {sid!r} (attendu : 'S' suivi de chiffres)")
    return value


class SourceCitee(BaseModel):
    id: str = Field(description="Identifiant de citation, ex. 'S1' (renvoyé par save_source)", pattern=r"^S\d+$")
    titre: str = Field(description="Titre de la source")
    url: str = Field(description="URL de la source")
    fiabilite: Literal["primaire", "secondaire", "faible"] = Field(description="Fiabilité estimée de la source")


class PointCle(BaseModel):
    affirmation: str = Field(description="Affirmation factuelle, appuyée par des sources")
    sources: list[str] = Field(description="Identifiants [Sn] des sources à l'appui, ex. ['S1', 'S2']")

    _check_ids = field_validator("sources")(valide_ids_sources)


class SyntheseVeille(BaseModel):
    sujet: str = Field(description="Sujet de la veille")
    date_veille: str = Field(description="Date de la veille au format AAAA-MM-JJ", pattern=r"^\d{4}-\d{2}-\d{2}$")
    veille_insuffisante: bool = Field(description="true si moins de 3 sources solides ont été trouvées")
    resume_executif: list[str] = Field(min_length=1, max_length=3, description="1 à 3 puces de synthèse exécutive")
    points_cles: list[PointCle] = Field(description="Affirmations clés, chacune avec ses citations [Sn]")
    divergences: list[str] = Field(default_factory=list, description="Divergences constatées entre sources")
    incertitudes: list[str] = Field(default_factory=list, description="Ce qui n'est pas tranché à l'issue de la veille")
    sources: list[SourceCitee] = Field(description="Liste complète des sources citées")

    @model_validator(mode="after")
    def sources_listées(self) -> "SyntheseVeille":
        listed = {s.id for s in self.sources}
        manquantes = sorted({sid for p in self.points_cles for sid in p.sources} - listed)
        if manquantes:
            raise ValueError(f"points_cles citent des sources absentes du champ 'sources' : {', '.join(manquantes)}")
        return self

    def cited_source_ids(self) -> set[str]:
        return {sid for p in self.points_cles for sid in p.sources} | {s.id for s in self.sources}

    def render_markdown(self) -> str:
        lignes = [f"# {self.sujet}", "", f"Date de la veille : {self.date_veille}", ""]
        if self.veille_insuffisante:
            lignes += ["> **Veille insuffisante** : moins de 3 sources solides, fiabilité limitée.", ""]
        lignes += ["## Résumé exécutif", ""]
        lignes += [f"- {p}" for p in self.resume_executif]
        lignes += ["", "## Points clés", ""]
        for p in self.points_cles:
            citations = "".join(f"[{s}]" for s in p.sources)
            lignes.append(f"- {p.affirmation} {citations}")
        if self.divergences:
            lignes += ["", "## Divergences entre sources", ""]
            lignes += [f"- {d}" for d in self.divergences]
        if self.incertitudes:
            lignes += ["", "## Incertitudes", ""]
            lignes += [f"- {i}" for i in self.incertitudes]
        lignes += ["", "## Sources", ""]
        for s in self.sources:
            lignes.append(f"- [{s.id}] {s.titre} — {s.url} — {s.fiabilite}")
        return "\n".join(lignes) + "\n"


class Indicateur(BaseModel):
    valeur: str | None = Field(description="Valeur publiée telle quelle, ex. '204 €' — null si non trouvée")
    date_valeur: str | None = Field(description="Date d'arrêté de la valeur, ex. '30/06/2026' — null si inconnue")
    sources: list[str] = Field(default_factory=list, description="Identifiants [Sn] à l'appui de ce chiffre")

    _check_ids = field_validator("sources")(valide_ids_sources)


class IndicateursScpi(BaseModel):
    prix_part: Indicateur = Field(description="Prix de souscription de la part")
    valeur_realisation: Indicateur = Field(description="Valeur de réalisation (hors frais)")
    valeur_reconstitution: Indicateur = Field(description="Valeur de reconstitution (avec frais) — ne pas confondre avec la valeur de réalisation")
    parts_attente_vente: Indicateur = Field(description="Nombre de parts en attente de retrait/vente et % de la capitalisation")
    valeur_retrait: Indicateur | None = None
    collecte_trimestre: Indicateur | None = None
    taux_distribution: Indicateur | None = None


class MediaScpi(BaseModel):
    titre: str = Field(description="Titre de l'article")
    url: str = Field(description="URL de l'article")
    date: str | None = Field(description="Date de publication si connue")
    resume: str = Field(description="Résumé en une phrase")


class VeilleScpi(BaseModel):
    scpi: str = Field(description="Nom de la SCPI, ex. 'Pierval Santé'")
    societe_gestion: str | None = Field(default=None, description="Société de gestion, ex. 'Euryale Asset Management'")
    date_veille: str = Field(description="Date de la veille au format AAAA-MM-JJ", pattern=r"^\d{4}-\d{2}-\d{2}$")
    periode: str | None = Field(default=None, description="Période du dernier document connu, ex. 'T3 2026'")
    indicateurs: IndicateursScpi
    medias: list[MediaScpi] = Field(default_factory=list, description="Actualité média récente (90 derniers jours)")
    evolution: list[str] = Field(default_factory=list, description="Variations constatées par rapport à la période précédente")
    incertitudes: list[str] = Field(default_factory=list, description="Champs non publiés, divergences, points de vigilance")
    veille_insuffisante: bool = Field(default=False, description="true si les documents officiels n'ont pas pu être trouvés")
    sources: list[SourceCitee] = Field(description="Liste complète des sources citées")

    @model_validator(mode="after")
    def sources_listées(self) -> "VeilleScpi":
        listed = {s.id for s in self.sources}
        citées = {sid for ind in self.indicateurs.model_dump().values() if isinstance(ind, dict) for sid in ind.get("sources", [])}
        manquantes = sorted(citées - listed)
        if manquantes:
            raise ValueError(f"les indicateurs citent des sources absentes du champ 'sources' : {', '.join(manquantes)}")
        return self

    def cited_source_ids(self) -> set[str]:
        citées = {sid for ind in self.indicateurs.model_dump().values() if isinstance(ind, dict) for sid in ind.get("sources", [])}
        return citées | {s.id for s in self.sources}

    def render_markdown(self) -> str:
        lignes = [
            f"# Veille SCPI — {self.scpi}",
            "",
            f"Date de la veille : {self.date_veille}" + (f" | Période suivie : {self.periode}" if self.periode else ""),
            f"Société de gestion : {self.societe_gestion or 'inconnue'}",
            "",
        ]
        if self.veille_insuffisante:
            lignes += ["> **Veille insuffisante** : documents officiels non trouvés.", ""]
        lignes += ["## Indicateurs", ""]
        noms = {
            "prix_part": "Prix de la part",
            "valeur_realisation": "Valeur de réalisation",
            "valeur_reconstitution": "Valeur de reconstitution",
            "parts_attente_vente": "Parts en attente de vente/retrait",
            "valeur_retrait": "Valeur de retrait",
            "collecte_trimestre": "Collecte du trimestre",
            "taux_distribution": "Taux de distribution",
        }
        for champ, ind in self.indicateurs:
            if ind is None:
                continue
            valeur = ind.valeur if ind.valeur is not None else "non publiée"
            date = f" (au {ind.date_valeur})" if ind.date_valeur else ""
            cit = "".join(f"[{s}]" for s in ind.sources)
            lignes.append(f"- **{noms.get(champ, champ)}** : {valeur}{date} {cit}".rstrip())
        if self.evolution:
            lignes += ["", "## Évolution vs période précédente", ""]
            lignes += [f"- {e}" for e in self.evolution]
        if self.medias:
            lignes += ["", "## Actualité média", ""]
            for m in self.medias:
                date = f" ({m.date})" if m.date else ""
                lignes.append(f"- {m.titre}{date} — {m.url} : {m.resume}")
        if self.incertitudes:
            lignes += ["", "## Incertitudes et points de vigilance", ""]
            lignes += [f"- {i}" for i in self.incertitudes]
        lignes += ["", "## Sources", ""]
        for s in self.sources:
            lignes.append(f"- [{s.id}] {s.titre} — {s.url} — {s.fiabilite}")
        lignes += ["", "> Cette veille est informative et ne constitue pas un conseil en investissement.", ""]
        return "\n".join(lignes) + "\n"


class VeillePortefeuille(BaseModel):
    date_veille: str = Field(description="Date de la veille au format AAAA-MM-JJ", pattern=r"^\d{4}-\d{2}-\d{2}$")
    scpis: list[VeilleScpi] = Field(min_length=1, description="Une veille VeilleScpi par SCPI du portefeuille")
    synthese: list[str] = Field(default_factory=list, description="Comparaison transversale entre les SCPI (rendement, liquidité, valorisation)")

    def cited_source_ids(self) -> set[str]:
        ids: set[str] = set()
        for v in self.scpis:
            ids |= v.cited_source_ids()
        return ids

    def render_markdown(self) -> str:
        parties = [f"# Veille portefeuille SCPI — {self.date_veille}", ""]
        for v in self.scpis:
            parties.append(v.render_markdown())
        if self.synthese:
            parties += ["# Comparaison transversale", ""]
            parties += [f"- {s}" for s in self.synthese]
            parties.append("")
        parties.append("> Cette veille est informative et ne constitue pas un conseil en investissement.")
        return "\n".join(parties) + "\n"