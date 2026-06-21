# Audit Project Agent

Agent IA d'audit technique de projets informatiques. Analyse le code source, l'architecture, les dépendances et la configuration d'un projet, puis génère un rapport structuré en Markdown et PDF.

## Fonctionnalités

- Interface web **Streamlit** et interface **CLI**
- Analyse via **Google Gemini** (gemini-2.5-flash par défaut)
- Rapport structuré en **11 blocs** couvrant 8 piliers d'analyse
- Génération automatique d'un **rapport PDF stylisé** (couleurs, badges de risque, mise en page professionnelle)
- Ingestion intelligente : priorité aux fichiers critiques, troncature automatique, budget de tokens maîtrisé
- Détection et exclusion automatique des environnements virtuels Python
- Détection de réponse dégénérée avec message d'erreur explicite
- Streaming : affichage du rapport en temps réel pendant la génération

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

## Prérequis

- Python 3.11+
- Une clé API Google Gemini — [obtenir une clé](https://aistudio.google.com/apikey)

## Installation

```bash
# Cloner le dépôt
git clone <url-du-repo>
cd audit-project-agent

# Créer l'environnement virtuel
python -m venv audit-agent-env
audit-agent-env\Scripts\activate      # Windows
# source audit-agent-env/bin/activate # Linux / macOS

# Installer les dépendances
pip install -r requirements.txt
```

## Configuration

Créer un fichier `.env` à la racine (ne jamais le committer) :

```env
GEMINI_API_KEY=votre_cle_api_ici
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.1
MAX_OUTPUT_TOKENS=65536
```

Voir [.env.example](.env.example) pour le modèle complet.

## Utilisation

### Interface web (recommandée)

```bash
streamlit run app.py
```

Ouvre `http://localhost:8501` dans le navigateur. Saisissez le chemin absolu du projet à auditer, puis cliquez sur **Lancer l'audit**. Le rapport s'affiche en temps réel et est téléchargeable en `.md` et `.pdf`.

### Interface CLI

```bash
# Audit standard
python main.py /chemin/vers/mon-projet

# Audit avec affichage en temps réel dans le terminal
python main.py /chemin/vers/mon-projet --stream
```

Dans les deux cas, les fichiers `audit_<projet>_<horodatage>.md` et `.pdf` sont déposés à la racine du projet audité si l'option de sauvegarde est activée.

## Structure du projet

```
audit-project-agent/
├── app.py                    # Interface web Streamlit
├── main.py                   # Interface CLI
├── config/
│   └── settings.py           # Chargement de la configuration (.env)
├── core/
│   ├── ingestion.py          # Chargement et priorisation des fichiers du projet
│   └── prompts.py            # Génération du prompt d'audit (11 blocs)
├── services/
│   ├── gemini_client.py      # Client Gemini avec retry et détection de dégénérescence
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

## Licence

Usage personnel et professionnel. Ne pas partager la clé API.
