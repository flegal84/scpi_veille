---
name: scpi-veille
description: "Veille périodique générique sur un portefeuille de SCPI (par défaut : Pierval Santé, Epargne Pierre, Iroko Zen, Transitions Europe, Corum Origin, Corum XL, Corum Eurion, Remake Live) — prix de la part, valeurs de réalisation/reconstitution/retrait, parts en attente de retrait, collecte, dividende/TD, TOF, actualité média 90 jours, comparaison transversale. Paramètre : la liste des SCPI à suivre."
---

# Veille SCPI (générique, multi-SCPI)

## Paramètre

La liste des SCPI à suivre, fournie par l'utilisateur (portefeuille par défaut :
Pierval Santé, Epargne Pierre, Iroko Zen, Transitions Europe, Corum Origin, Corum XL,
Corum Eurion, Remake Live).
**« Epargne Pierre » désigne la SCPI Epargne Pierre (France) — PAS « Epargne Pierre
Europe »** : deux SCPI distinctes d'Atland Voisin, prix de part différents (20,80 € vs 20 €).
Ne jamais mélanger leurs chiffres ; si « Epargne Pierre Europe » est demandé explicitement,
la traiter comme une SCPI à part entière et le dire clairement dans le rapport.

## Sociétés de gestion et sources primaires (vérifier via recherche web si le site a changé)
   SCPI | Société de gestion | Site officiel |
 | --- | --- | --- |
 | Pierval Santé | Euryale AM | euryale-am.fr/nos-solutions/pierval-sante/ + bulletins PDF `BT_PIERVAL_SANTE_YYYY_Tq.pdf` |
 | Epargne Pierre (France) — Epargne Pierre Europe uniquement si demandé explicitement | Atland Voisin | atland-voisin.com/scpi/... |
 | Iroko Zen | Iroko | iroko.eu |
 | Transitions Europe | Arkéa REIM | arkea-reim.com |
 | Corum Origin / Corum XL / Corum Eurion | Corum AM (Corum L'Épargne) | corum.fr/nos-scpi/... |
 | Remake Live | Remake AM | remake.fr/remake-live/ |

Pour toute autre SCPI : rechercher « <nom SCPI> société de gestion bulletin trimestriel
site officiel ».

**Note Atland Voisin (Epargne Pierre*)** : depuis le 01/07/2026, division par dix du nominal
(208 € → 20,80 €) — les bulletins affichent les valeurs en « ancienne part » (×10) :
toujours préciser l'unité et reconvertir. La valeur de reconstitution (avec valeur vénale
et valeur de réalisation) est en **note de bas de page du bulletin PDF** ; le backlog
« parts en attente de retrait » est en **pages 1-4 du bulletin**. Lire le PDF directement. Lire les bulletins PDF avec l'outil de lecture de pages (extraction PDF).
Presse spécialisée : pierrepapier.fr, francescpi.com, portail-scpi.fr, scpiselect.fr,
centraledesscpi.com, meilleurescpi.com, scpi-lab.com ; médias généralistes pour l'actu.

## Champs à extraire par SCPI (date d'arrêté obligatoire)

- prix de la part (souscription) ;
- valeur de réalisation, valeur de reconstitution, valeur de retrait (**trois chiffres distincts, ne pas confondre**) ;
- nombre de parts en attente de retrait/vente et % de la capitalisation (indicateur de liquidité) ;
- collecte brute/nette du trimestre, dividende du trimestre, taux de distribution annuel, TOF ;
- capitalisation, nombre d'actifs/associés, endettement si publié.

Règles : chaque chiffre = valeur + date d'arrêté + citation `[Sn]`. Comparer à la période
précédente quand c'est possible. Champ non publié → `null` + explication dans `incertitudes`.

- **TOF obligatoire, valeur chiffrée exigée** : chercher explicitement le « taux
  d'occupation financier » dans le bulletin de la société de gestion (section
  gestion/patrimoine). Un commentaire qualitatif (« en baisse », « solide ») ne remplace
  **jamais** la valeur. Même exigence pour tous les champs : valeur chiffrée + date
  d'arrêté ; si vraiment introuvable → `null` + incertitude explicite.

## Médias

Actualité des **90 derniers jours** par SCPI : titre, url, date, résumé d'une phrase.

## Sortie

JSON conforme au schéma `VeillePortefeuille` : `date_veille`, `scpis[]` (un objet
`VeilleScpi` par SCPI : scpi, societe_gestion, periode, indicateurs, medias, evolution,
incertitudes, sources), `synthese[]` (comparaison transversale entre les SCPI).
Puis `save_synthesis` avec le JSON complet.

## Garde-fous

- Source primaire (société de gestion) obligatoire pour les chiffres clés, croisée avec
  au moins un média.
- **Tout chiffre venant d'une source secondaire** (presse, agrégateurs, plateformes de
  marché secondaire type 2nd Market) doit être **recoupé avec le bulletin/rapport officiel
  de la société de gestion** avant d'entrer dans `indicateurs`. S'il ne peut pas l'être :
  il reste dans `medias` ou `incertitudes`, noté « non vérifié, source secondaire ».
  Ne jamais confondre rotation du marché secondaire et backlog de demandes de retrait.
- N'invente jamais une valeur ; `null` + incertitude si non publiée.
- Cette veille est **informative** : ce n'est pas un conseil en investissement. Renvoie
  toujours vers les documents officiels publiés par les sociétés de gestion.