# veille-agent

Projet fil rouge « agents & skills » : un agent de veille qui produit des
**synthèses sourcées** (citations `[Sn]` vérifiées dans un registre local).

## Structure
veille-agent/
├── SPEC.md                  fiche d'identité de l'agent (objectif, garde-fous, métriques)
├── main.py                  agent générique (Mistral Agents SDK 1.1.0, output_type=SyntheseVeille)
├── scpi.py                  agent SCPI multi-portefeuille (output_type=VeillePortefeuille) + historique
├── models.py                schémas Pydantic : SyntheseVeille + VeilleScpi (sortie structurée)
├── tools.py                 outils: web_search, search_arxiv, fetch_url (HTML + PDF), save_source, find_source, list_saved_sources, save_synthesis
├── skills/veille-synthese/   skill générique chargé à la demande (skill.read)
├── skills/scpi-veille/        skill SCPI générique multi-SCPI (sociétés de gestion, champs, règles)
├── skills/scpi-pierval-sante/ skill SCPI Pierval Santé (plongée détaillée)
│   └── SKILL.md
│   └── SKILL.md
├── eval/                    jeu de cas + scoring heuristique + runner
│   ├── cases.json
│   ├── scoring.py
│   └── run_eval.py
└── tests/                   tests unitaires (hors ligne)

## Installation

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[test]"
Configuration
Crée une clé API Mistral dans ton workspace (console Mistral → API keys) :

export MISTRAL_API_KEY="..."
Variables optionnelles : VEILLE_MODEL (défaut mistral-large-4),
VEILLE_SANDBOX (bashkit par défaut en local, mistral pour un sandbox Mistral,
none sans sandbox — incompatible avec les skills).

Utilisation
.venv/bin/python main.py "Veille sur les agents LLM : tendances 2026 ?"
.venv/bin/python scpi.py               # veille du portefeuille par défaut (8 SCPI)
.venv/bin/python scpi.py "Corum Origin" "Iroko Zen"   # veille sur une sélection de SCPI
.venv/bin/agents chat                 # chat interactif, affiche chaque appel d'outil
.venv/bin/agents info                 # vérifie l'entrypoint sans appeler le modèle
Veille SCPI périodique
Chaque run de scpi.py enregistre le JSON structuré dans data/historique/veille-portefeuille-<timestamp>.json
et la synthèse Markdown dans data/syntheses/.

Option A — cron local (fonctionne dès maintenant) : wrapper veille_cron.sh (charge .env, loggue
dans logs/veille-cron.log) ; crontab hebdomadaire (lundi 8h) :

0 8 * * 1 /chemin/vers/veille-agent/veille_cron.sh
Option B — périodicité managée dans Mistral Studio (sans machine locale) : pousser le projet sur un
dépôt Git, puis agents deploy (enregistre le workflow scpi-veille-portefeuille), puis
create_workflow_schedule (ex. cron 0 8 * * 1, time_zone_name: Europe/Paris). Chaque exécution
apparaît en traces dans AI Studio (search_traces / aggregate_traces : historique, outils appelés,
coûts). Run manuel : trigger_workflow_schedule. Alternative sans déploiement : webhook externe
(cron-job.org…) → create_trigger.

Tests et évaluation
.venv/bin/python -m pytest -q                       # tests hors ligne des outils et du scoring
MISTRAL_API_KEY=... .venv/bin/python eval/run_eval.py  # évalue l'agent sur eval/cases.json → eval/results.json
Fonctionnement
Le modèle voit le nom et la description du skill veille-synthese et le charge avec skill.read quand la tâche s'y prête.
Il recherche (web_search, search_arxiv), lit les pages (fetch_url) et enregistre chaque source (save_source → [S1], [S2], ...).
La réponse finale est structurée : output_type=SyntheseVeille (Pydantic) contraint le JSON de sortie ; state.output est l'objet typé (ou InvalidOutput). Le schéma valide le format des [Sn], la date, et la cohérence points_cles ↔ sources.
save_synthesis reçoit ce même JSON, refuse toute synthèse qui cite un [Sn] non enregistré, puis rend le Markdown côté code (render_markdown) : la cohérence des citations et le rendu sont garantis par le code, pas par le prompt.
---

✅ **C'est tout le projet** — récapitulatif des fichiers à recréer dans ton dépôt :
pyproject.toml · .gitignore · conftest.py (vide) · veille_cron.sh
main.py · scpi.py · tools.py · models.py
SPEC.md · README.md
skills/veille-synthese/SKILL.md · skills/scpi-veille/SKILL.md
eval/cases.json · eval/scoring.py · eval/run_eval.py
tests/test_tools.py · test_models.py · test_models_scpi.py · test_models_portefeuille.py · test_scoring.py · test_portefeuille.py
tests/fixtures/ddg_sample.html · tests/fixtures/arxiv_sample.xml

(Note : dans le README ci-dessus, l'arbre duplique une ligne `│   └── SKILL.md` — au moment de recréer, garde une seule entrée par dossier de skill. `skills/scpi-pierval-sante/SKILL.md` est facultatif, il existe déjà dans ton registre.)

Une fois recréé : `python3.12 -m venv .venv && .venv/bin/pip install -e ".[test]"`, mets ta `MISTRAL_API_KEY` dans `.env`, teste avec `.venv/bin/python -m pytest -q` (33 tests), puis `git add/commit/push` + PR. Besoin d'autre chose ?


18:08

Projet fil rouge agents IA

