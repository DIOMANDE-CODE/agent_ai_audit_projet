# CodePulse

Agent IA d'audit technique de projets informatiques. Analyse le code source, l'architecture, les dépendances et la configuration d'un projet, puis génère un rapport structuré en Markdown et PDF.

## Fonctionnalités

- Commande `audit` installable en une ligne depuis n'importe quel terminal (CMD, PowerShell, bash)
- Clé API embarquée — aucune configuration requise après installation
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

## Installation

### Via PyPI (recommandé)

```bash
pip install agent-audit-ai
audit .
```

Aucune configuration requise — la clé API est embarquée dans le package.

### Via l'exécutable Windows

Télécharger `audit.exe` depuis la page [Releases GitHub](https://github.com/DIOMANDE-CODE/agent_ai_audit_projet/releases), le placer dans `C:\Windows\System32\` et l'utiliser directement :

```cmd
audit .
```

### Via le code source

```bash
git clone https://github.com/DIOMANDE-CODE/agent_ai_audit_projet.git
cd agent_ai_audit_projet

python -m venv codepulse-env
codepulse-env\Scripts\activate        # Windows
# source codepulse-env/bin/activate   # Linux / macOS

pip install -e .
audit .
```

---

## Utilisation

```bash
# Auditer le dossier courant
audit .

# Auditer un projet spécifique
audit /chemin/vers/mon-projet

# Afficher le rapport en temps réel pendant la génération
audit /chemin/vers/mon-projet --stream

# Aide
audit --help
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
agent_ai_audit_projet/
├── main.py                   # CLI — commande `audit`
├── app.py                    # Interface web Streamlit (optionnelle)
├── pyproject.toml            # Packaging pip (agent-audit-ai)
├── Dockerfile                # Image production (python:3.12-slim, non-root, healthcheck)
├── .dockerignore
├── .github/
│   └── workflows/
│       └── publish.yml       # CI/CD : build exe + publication PyPI
├── components/
│   └── folder_picker/        # Composant sélection de dossier (File System Access API)
│       └── index.html
├── config/
│   ├── settings.py           # Configuration : _bundled → st.secrets → .env → env vars
│   └── _bundled.py           # Clé API embarquée (gitignore)
├── core/
│   ├── ingestion.py          # Chargement et priorisation des fichiers du projet
│   └── prompts.py            # Génération du prompt d'audit (11 blocs)
├── services/
│   ├── gemini_client.py      # Client Gemini avec retry et streaming
│   └── pdf_generator.py      # Génération PDF via ReportLab
├── requirements.txt
├── .env.example              # Modèle de configuration
├── .gitignore
├── LICENSE
├── README.md
└── CHANGELOG.md
```

## Variables d'environnement

> Non requis si la clé est embarquée dans le package distribué.

| Variable | Défaut | Description |
|---|---|---|
| `GEMINI_API_KEY` | *(embarquée)* | Clé API Google Gemini |
| `MODEL_NAME` | `gemini-2.5-flash` | Modèle Gemini à utiliser |
| `TEMPERATURE` | `0.1` | Créativité du modèle (0 = déterministe) |
| `MAX_OUTPUT_TOKENS` | `65536` | Budget de tokens pour la réponse |

Priorité de lecture : clé embarquée (`_bundled.py`) → `st.secrets` → `.env` → variables d'environnement système.

## Licence

MIT — voir [LICENSE](LICENSE).
