---
name: veille-synthese
description: Procédure de veille et de synthèse sourcée. À utiliser dès que l'utilisateur demande une veille, un état de l'art ou une synthèse d'actualité sur un sujet (technologie, marché, réglementation...).
---

# Veille et synthèse sourcée

Applique cette procédure pour toute demande de veille ou de synthèse.

## 1. Cadrer

Reformule le sujet en une question précise. Si le périmètre est flou (période,
zone géographique, type de sources), pose une question courte avant de chercher.

## 2. Collecter

- Lance plusieurs recherches complémentaires avec `web_search` (formulations
  variées, en anglais et en français si pertinent) et `search_arxiv` pour la
  veille scientifique.
- Vise au moins 5 sources primaires ou de bonne qualité ; écarte les pages sans
  auteur, sans date, ou purement promotionnelles.
- Pour chaque source retenue, lis le contenu réel avec `fetch_url` (ne te fie
  pas qu'à l'extrait), puis enregistre-la avec `save_source`, qui renvoie un
  identifiant de citation `[Sn]`.

## 3. Vérifier et croiser

- Confronte chaque affirmation clé sur au moins 2 sources indépendantes.
- Note les divergences entre sources ; ne les résous pas silencieusement.

## 4. Synthétiser en JSON structuré

Ta réponse finale est un objet JSON conforme au schéma de sortie, avec :

- `sujet` : le sujet traité ;
- `date_veille` : date du jour au format `AAAA-MM-JJ` ;
- `veille_insuffisante` : `true` si moins de 3 sources solides ;
- `resume_executif` : 1 à 3 puces maximum ;
- `points_cles` : liste d'objets `{affirmation, sources}`, où `sources` est la
  liste des identifiants `[Sn]` (ex. `["S1", "S2"]`) appuyant l'affirmation ;
- `divergences` : ce qui diverge entre sources ;
- `incertitudes` : ce qui n'est pas tranché ;
- `sources` : la liste complète des sources citées `{id, titre, url, fiabilite}`
  (`fiabilite` : `primaire`, `secondaire` ou `faible`). Tout `[Sn]` cité dans
  `points_cles` doit figurer dans `sources`.

## 5. Enregistrer

Passe ce même objet JSON à `save_synthesis` : il est refusé s'il cite un `[Sn]`
non enregistré ou s'il ne cite aucune source. La synthèse est alors écrite en
Markdown dans `data/syntheses/`.

## Garde-fous

- Ne cite jamais une source que tu n'as pas lue via `fetch_url`.
- N'invente jamais une statistique, une date ou un nom.
- Si tu as moins de 3 sources solides : `veille_insuffisante: true` et explique
  pourquoi dans `incertitudes`.
- Indique la date de la veille dans `date_veille`.