# Changelog

## [1.0.0] — 2026-06-23

### Ajouté
- Composant **sélecteur de dossier natif** dans le navigateur (`components/folder_picker/`) via File System Access API (`showDirectoryPicker`) — aucun ZIP manuel, aucune popup d'import navigateur
- Spinner animé + barre de progression pendant la compression JSZip côté navigateur
- Support **Streamlit Cloud Secrets** : lecture de `st.secrets` en priorité sur `.env`
- Interface web **Streamlit** (`app.py`) avec streaming en temps réel, sidebar verrouillée et boutons de téléchargement MD + PDF
- Génération de rapport PDF stylisé via ReportLab (pure Python, sans dépendance système)
- Badges colorés de niveau de risque dans le PDF : CRITIQUE, ÉLEVÉ, MOYEN, FAIBLE, INFO
- Pied de page PDF avec numéro de page et mention confidentielle
- Détection de réponse dégénérée (remplissage par des espaces ou ligne unique géante)
- Détection automatique des environnements virtuels Python (via `pyvenv.cfg`) à l'ingestion
- `ThinkingConfig.thinking_budget=10000` pour plafonner les tokens de raisonnement interne de Gemini
- Fichier `.env.example` comme modèle de configuration
- **CLI `audit`** : commande installable via `pip install agent-audit-ai`, sortie terminal enrichie avec `rich` (étapes colorées, spinner, séparateurs)
- **Clé API embarquée** (`config/_bundled.py`, gitignore) : aucune configuration requise après installation
- **Configuration automatique au premier lancement** : si aucune clé trouvée, saisie interactive + sauvegarde dans `~/.env`
- **`pyproject.toml`** : packaging complet avec métadonnées, classifiers, license MIT, entry point `audit`
- **`LICENSE`** : licence MIT
- **CI/CD GitHub Actions** (`.github/workflows/publish.yml`) :
  - Build `audit.exe` (PyInstaller) à chaque push sur `main` → artifact téléchargeable
  - Build `audit.exe` + publication PyPI automatique à chaque Release GitHub
  - Déclenchement manuel via `workflow_dispatch`
  - Trusted Publishing PyPI (OIDC) — sans token API à gérer

### Modifié
- Nom du projet : **CodePulse** (commande `audit`, package PyPI `agent-audit-ai`)
- Mode **100 % en ligne** : suppression du mode local tkinter, sélection de dossier via composant HTML dans le navigateur
- Bouton "Lancer l'audit" verrouillé (`audit_en_cours`) pendant toute la durée de l'analyse, avec reset garanti via `try/finally` + `st.rerun()`
- Résultats de l'audit stockés en `st.session_state` — bouton déverrouillé et rapport affiché après rerun
- Extraction ZIP via `io.BytesIO` — supprime l'écriture disque intermédiaire
- Streaming O(n) : accumulation par concaténation au lieu de `"".join(chunks)` à chaque chunk
- Import `streamlit` hoissé en singleton module-level dans `settings.py` — exécuté une seule fois
- `MAX_OUTPUT_TOKENS` relevé à 65536 pour garantir la génération des 11 blocs complets
- Remplacement de WeasyPrint (nécessitait GTK3 sur Windows) par ReportLab
- Priorité de lecture de la clé API : `_bundled` → `st.secrets` → `.env` → variables d'environnement

### Corrigé
- Erreur PDF ReportLab `too large on page` : blocs de code découpés en chunks de 55 lignes max pour tenir dans le frame de page
- `StreamlitSecretNotFoundError` au démarrage sur Render : `_lire_secret` utilisait l'opérateur `in` sur `st.secrets` → remplacé par `st.secrets.get()` avec `except Exception`
- Dockerfile : port hardcodé `8501` ignorait la variable `PORT` injectée par Render → `CMD` mis à jour avec `--server.port ${PORT:-8501}`
- Rapports illisibles sur Windows : normalisation des fins de ligne (`\r\n` → `\n`)
- Troncature du rapport au BLOC 4 : budget de tokens insuffisant (thinking tokens Gemini non comptés)
- Ingestion du dossier `audit-agent-env/` (venv non standard) : détection générique via `pyvenv.cfg`

### Docker
- **Dockerfile** production-ready : image `python:3.12-slim`, utilisateur non-root `appuser`, variables d'environnement Streamlit intégrées, `HEALTHCHECK` sur `/_stcore/health`
- **BuildKit cache mount** : rebuild sans re-télécharger les wheels si `requirements.txt` est inchangé
- **`--compile`** sur `pip install` : pré-compilation des `.pyc` au build → démarrage du conteneur plus rapide
- **`.dockerignore`** : exclut `.env`, venvs, caches, rapports générés et secrets Streamlit

### Supprimé
- Dépendance WeasyPrint et ses 7 dépendances exclusives : `pydyf`, `pyphen`, `tinycss2`, `tinyhtml5`, `cssselect2`, `zopfli`, `webencodings` (~30 MB en moins dans l'image Docker)
- Option CLI `--sortie` (les rapports vont toujours à la racine du projet audité)
- Scripts `lancer.bat` / `lancer.sh` (mode local supprimé)
- Mode local tkinter
