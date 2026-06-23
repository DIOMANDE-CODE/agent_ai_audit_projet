# CodePulse

Agent IA d'audit technique de projets informatiques. Analyse le code source, l'architecture, les dépendances et la configuration d'un projet, puis génère un rapport structuré en Markdown et PDF.

## Fonctionnalités

- Commande `pulse` installable dans le terminal (CMD, PowerShell, bash)
- Analyse via **Google Gemini 2.5 Flash**
- Rapport structuré en **11 blocs** couvrant 8 piliers d'analyse
- Génération automatique d'un **rapport PDF stylisé** (couleurs, badges de risque, mise en page professionnelle)
- Ingestion intelligente : priorité aux fichiers critiques, troncature automatique, budget de tokens maîtrisé
- Exclusion automatique des fichiers sensibles (`.env`, `node_modules`, `__pycache__`, venvs…)
- Streaming : affichage du rapport en temps réel pendant la génération
- Interface web optionnelle (Streamlit) pour les non-développeurs
- Compatible **Streamlit Cloud** et **Render** : clé API configurable via variables d'environnement

## Piliers analysés

| # | Pilier |
|---|--------|
| 1 | Architecture & Qualité du code |
| 2 | Tests & Qualité Assurance |
| 3 | Sécurité & Robustesse (OWASP Top 10) |
| 4 | DevOps & Infrastructure |
| 5 | Performance & Scalabilité |
| 6 | Dépendances & Licences |
| 7 | Conformité & Réglementation (RGPD, WCAG) |
| 8 | Documentation & Expérience Développeur |

---

## Installation en ligne de commande

### Prérequis

- Python 3.12+
- Une clé API Google Gemini — [obtenir une clé](https://aistudio.google.com/apikey)

### Étapes

```bash
git clone <url-du-repo>
cd audit-project-agent

python -m venv codepulse-env
codepulse-env\Scripts\activate        # Windows CMD / PowerShell
# source codepulse-env/bin/activate   # Linux / macOS

pip install -e .
```

### Configurer la clé API (une seule fois)

```bash
# Windows CMD
echo GEMINI_API_KEY=votre_cle_api_ici >> %USERPROFILE%\.env

# Windows PowerShell
Add-Content "$env:USERPROFILE\.env" "GEMINI_API_KEY=votre_cle_api_ici"

# Linux / macOS
echo "GEMINI_API_KEY=votre_cle_api_ici" >> ~/.env
```

### Utilisation

```bash
# Auditer un projet
pulse /chemin/vers/mon-projet

# Auditer le dossier courant
pulse .

# Afficher le rapport en temps réel
pulse /chemin/vers/mon-projet --stream
```

Les rapports `.md` et `.pdf` sont générés à la racine du projet audité.

---

## Interface web (optionnelle)

Pour les utilisateurs non-développeurs, une interface Streamlit est disponible.

### Déploiement sur Render

1. Poussez le dépôt sur GitHub
2. Sur [render.com](https://render.com) → **New → Web Service** → connecter le repo
3. Runtime : **Docker** (Render détecte automatiquement le `Dockerfile`)
4. Dans **Environment → Environment Variables**, ajouter :

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | votre clé API Gemini |

5. Cliquer **Create Web Service** — Render construit l'image et expose l'URL publique.

### Déploiement sur Streamlit Cloud

1. Forkez / poussez ce dépôt sur GitHub
2. Connectez-le à [share.streamlit.io](https://share.streamlit.io)
3. Dans **Settings → Secrets**, ajoutez :

```toml
GEMINI_API_KEY = "votre_cle_api_ici"
```

### Docker (local)

```bash
DOCKER_BUILDKIT=1 docker build -t codepulse .
docker run -p 8501:8501 -e GEMINI_API_KEY=votre_cle_api codepulse
```

---

## Structure du projet

```
audit-project-agent/
├── main.py                   # CLI — commande `pulse`
├── app.py                    # Interface web Streamlit (optionnelle)
├── pyproject.toml            # Packaging — rend `pulse` installable
├── Dockerfile                # Image production (python:3.12-slim, non-root, healthcheck)
├── .dockerignore
├── components/
│   └── folder_picker/        # Composant sélection de dossier (File System Access API)
│       └── index.html
├── config/
│   └── settings.py           # Configuration : .env (CWD) → .env (~) → env vars
├── core/
│   ├── ingestion.py          # Chargement et priorisation des fichiers du projet
│   └── prompts.py            # Génération du prompt d'audit (11 blocs)
├── services/
│   ├── gemini_client.py      # Client Gemini avec retry et streaming
│   └── pdf_generator.py      # Génération PDF via ReportLab
├── requirements.txt
├── .env                      # Secrets — NE PAS COMMITTER
├── .env.example              # Modèle de configuration
├── .gitignore
├── README.md
└── CHANGELOG.md
```

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(obligatoire)* | Clé API Google Gemini |
| `MODEL_NAME` | `gemini-2.5-flash` | Modèle Gemini à utiliser |
| `TEMPERATURE` | `0.1` | Créativité du modèle (0 = déterministe) |
| `MAX_OUTPUT_TOKENS` | `65536` | Budget de tokens pour la réponse |

La lecture suit la priorité : `.env` (dossier courant) → `~/.env` (home) → variables d'environnement système → `st.secrets` (Streamlit Cloud).

## Licence

Usage personnel et professionnel. Ne pas partager la clé API.
