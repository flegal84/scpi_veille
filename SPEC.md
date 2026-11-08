# SPEC — Agents « veille-synthese » et « scpi-veille-pierval-sante »

## Objectif
Produire des synthèses de veille **sourcées et vérifiées** sur un sujet donné :
recherche web/arXiv → lecture des sources → enregistrement dans un registre de
citations → synthèse Markdown avec citations `[Sn]` → incertitudes explicites.

## Déclencheurs
Toute demande de type « veille sur X », « état de l'art de Y », « quelles sont les
tendances de Z », « résume-moi l'actualité sur W ».

## Capacités (outils)
   Outil | Rôle | Effets de bord |
 | --- | --- | --- |
 | `web_search(query, max_results)` | Résultats web (DuckDuckGo HTML) : titre, URL, extrait | aucun |
 | `search_arxiv(query, max_results)` | Preprints arXiv récents (veille scientifique) | aucun |
 | `fetch_url(url, max_chars)` | Télécharge et convertit une page en texte | aucun |
 | `save_source(url, title, key_points, reliability)` | Enregistre une source, renvoie `[Sn]` | écrit `data/sources.json` |
 | `save_synthesis(topic, synthese_json)` | Enregistre la synthèse finale (JSON `SyntheseVeille`), la rend en Markdown | écrit `data/syntheses/<sujet>.md` |

## Skill
`skills/veille-synthese/SKILL.md` (chargé à la demande via `skill.read`) : procédure
en 5 étapes (cadrer → collecter → vérifier/croiser → synthétiser → enregistrer) et
garde-fous. Le SDK ne sert que le corps du `SKILL.md` : le fichier doit être
autonome.

## Garde-fous
- Sortie structurée : `output_type=SyntheseVeille` (Pydantic) sur l'agent ; `Completed.output`
  est typé, `InvalidOutput` sinon. Le schéma Pydantic valide aussi le format des `[Sn]`,
  la date, et la cohérence points_cles ↔ sources.
- Aucune citation sans source enregistrée : `save_synthesis` **refuse** la synthèse
  si elle cite un `[Sn]` inconnu ou si elle ne cite rien.
- Ne jamais inventer de source, statistique ou date (imposé par le skill).
- Minimum 3 sources solides ; sinon la synthèse doit dire que la veille est
  insuffisante.
- Divergences entre sources rapportées, jamais résolues silencieusement.
- `fetch_url` n'accepte que des URL `http(s)` complètes.

## Format de sortie attendu
Objet `SyntheseVeille` (JSON) : `sujet`, `date_veille`, `veille_insuffisante`,
`resume_executif` (≤ 3 puces), `points_cles` (affirmation + `[Sn]`), `divergences`,
`incertitudes`, `sources`. Le Markdown rendu est produit par le code
(`render_markdown`), pas par le modèle.

## Métriques d'évaluation (voir `eval/`)
- Taux de synthèses avec ≥ 3 citations valides.
- Taux de citations résolubles dans le registre (`[Sn]` existants).
- Présence d'une section « incertitudes » quand les cas l'exigent.
- Fraîcheur des sources (dates de publication citées).

## Limites connues
- DuckDuckGo HTML peut limiter le débit ; arXiv ne couvre que la littérature scientifique.
- Pas de mémoire entre les runs (chaque `agent.run` est une nouvelle session).
- Le juge d'évaluation est heuristique (hors ligne) sur la sortie structurée ;
  un juge LLM est possible via le SDK `mistralai-evaluations` (réservé Enterprise ici).
- `output_type` contraint la réponse finale, pas les réponses intermédiaires.

## Agent SCPI multi-portefeuille (`scpi.py`)
Agent `scpi-veille-portefeuille` : mêmes outils + `find_source` / `list_saved_sources`
(dédup du registre entre veilles), `fetch_url` avec extraction PDF (bulletins trimestriels),
`output_type=VeillePortefeuille`. Portefeuille par défaut : Pierval Santé, Epargne Pierre,
Iroko Zen, Transitions Europe, Corum Origin (surchargeable en arguments CLI). Par SCPI :
prix de la part, valeur de réalisation/reconstitution/retrait, parts en attente de
retrait/vente (% capitalisation), collecte, dividende/TD, TOF + médias 90 jours + synthèse
comparative transversale. Chaque run historisé dans `data/historique/`.
Skill générique `scpi-veille` (mapping SCPI → société de gestion : Euryale AM, Atland Voisin,
Iroko, Arkéa REIM, Corum AM) ; `scpi-pierval-sante` reste dispo pour une plongée détaillée.
Disclaimer intégré : veille informative, pas un conseil en investissement.

## Pistes d'amélioration
- Mémoire de session (`create_session`) pour les veilles suivies dans le temps.
- Connecteur de recherche dédié (Brave/Google) au lieu du scraping DDG.
- Déploiement managé (`agents deploy`) + traces dans AI Studio.