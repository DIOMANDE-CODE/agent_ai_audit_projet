# Changelog

## [Unreleased]

### Ajouté
- Interface web **Streamlit** (`app.py`) avec streaming en temps réel, sidebar verrouillée et boutons de téléchargement MD + PDF
- Génération de rapport PDF stylisé via ReportLab (pure Python, sans dépendance système)
- Badges colorés de niveau de risque dans le PDF : CRITIQUE, ÉLEVÉ, MOYEN, FAIBLE, INFO
- Pied de page PDF avec numéro de page et mention confidentielle
- Détection de réponse dégénérée (remplissage par des espaces ou ligne unique géante)
- Détection automatique des environnements virtuels Python (via `pyvenv.cfg`) à l'ingestion
- Estimation du nombre de tokens consommés affichée à l'ingestion
- `ThinkingConfig.thinking_budget=10000` pour plafonner les tokens de raisonnement interne de Gemini
- Fichier `.env.example` comme modèle de configuration
- Fichiers `.gitignore`, `README.md` et `CHANGELOG.md`

### Modifié
- Les rapports (.md et .pdf) sont désormais générés à la **racine du projet audité**
- `MAX_OUTPUT_TOKENS` relevé à 65536 pour garantir la génération des 11 blocs complets
- Remplacement de WeasyPrint (nécessitait GTK3 sur Windows) par ReportLab
- Caractère de séparation `─` remplacé par `-` dans la CLI (compatibilité Windows cp1252)
- Sidebar Streamlit verrouillée en position ouverte (bouton de repli masqué via CSS)

### Corrigé
- Rapports illisibles sur Windows : normalisation des fins de ligne (`\r\n` → `\n`)
- Troncature du rapport au BLOC 4 : budget de tokens insuffisant (thinking tokens Gemini non comptés)
- Remplissage par des espaces : suppression des instructions de génération de tableaux dans le prompt
- Ingestion du dossier `audit-agent-env/` (venv non standard) : détection générique via `pyvenv.cfg`
- `app.py` : imports obsolètes (`CodeIngestor`, `get_audit_prompt`, `generate_audit_report`) remplacés par l'API actuelle

### Supprimé
- Dépendance WeasyPrint (remplacée par ReportLab)
- Option CLI `--sortie` (les rapports vont toujours à la racine du projet audité)
