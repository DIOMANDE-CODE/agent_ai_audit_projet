# Audit Project Agent

Agent IA d'audit technique de projets informatiques. Analyse le code source, l'architecture, les dépendances et la configuration d'un projet, puis génère un rapport structuré en Markdown et PDF.

## Fonctionnalités

- Interface web **Streamlit** — sélection de dossier native dans le navigateur (File System Access API)
- Analyse via **Google Gemini 2.5 Flash**
- Rapport structuré en **11 blocs** couvrant 8 piliers d'analyse
- Génération automatique d'un **rapport PDF stylisé** (couleurs, badges de risque, mise en page professionnelle)
- Ingestion intelligente : priorité aux fichiers critiques, troncature automatique, budget de tokens maîtrisé
- Exclusion automatique des fichiers sensibles (`.env`, `node_modules`, `__pycache__`, venvs…)
- Streaming : affichage du rapport en temps réel pendant la génération
- Compatible **Streamlit Cloud** et **Render** : clé API configurable via variables d'environnement, aucun `secrets.toml` requis

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

## Déploiement en ligne (Streamlit Cloud)

1. Forkez / poussez ce dépôt sur GitHub
2. Connectez-le à [share.streamlit.io](https://share.streamlit.io)
3. Dans **Settings → Secrets**, ajoutez :

```toml
GEMINI_API_KEY = "votre_cle_api_ici"
```

Les utilisateurs accèdent directement à l'URL publique — aucune configuration requise de leur côté.

## Déploiement sur Render

1. Poussez le dépôt sur GitHub
2. Sur [render.com](https://render.com) → **New → Web Service** → connecter le repo
3. Runtime : **Docker** (Render détecte automatiquement le `Dockerfile`)
4. Dans **Environment → Environment Variables**, ajouter :

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | votre clé API Gemini |

5. Cliquer **Create Web Service** — Render construit l'image et expose l'URL publique.

> Le Dockerfile lit automatiquement la variable `PORT` injectée par Render — aucune configuration de port manuelle requise.

## Déploiement Docker (local)

```bash
# Build (nécessite BuildKit)
DOCKER_BUILDKIT=1 docker build -t audit-project-agent .

# Lancer avec la clé API
docker run -p 8501:8501 -e GEMINI_API_KEY=votre_cle_api audit-project-agent
```

L'application est accessible sur [http://localhost:8501](http://localhost:8501).

> Le `.dockerignore` exclut automatiquement `.env` et les secrets — ne pas passer la clé via `COPY`.

## Installation locale (développeurs)

### Prérequis

- Python 3.12+
- Une clé API Google Gemini — [obtenir une clé](https://aistudio.google.com/apikey)

### Étapes

```bash
git clone <url-du-repo>
cd audit-project-agent

python -m venv audit-agent-env
audit-agent-env\Scripts\activate      # Windows
# source audit-agent-env/bin/activate # Linux / macOS

pip install -r requirements.txt
```

Créer un fichier `.env` à la racine (ne jamais le committer) :

```env
GEMINI_API_KEY=votre_cle_api_ici
```

Lancer l'interface web :

```bash
streamlit run app.py
```

## Structure du projet

```
audit-project-agent/
├── app.py                    # Interface web Streamlit
├── Dockerfile                # Image production (python:3.12-slim, non-root, healthcheck)
├── .dockerignore
├── components/
│   └── folder_picker/        # Composant de sélection de dossier (File System Access API)
│       └── index.html
├── config/
│   └── settings.py           # Configuration : st.secrets → .env → variables d'environnement
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

La lecture suit la priorité : `st.secrets` (Streamlit Cloud) → `.env` → variables d'environnement système.

## Licence

Usage personnel et professionnel. Ne pas partager la clé API.
