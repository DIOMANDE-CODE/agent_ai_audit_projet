# Changelog

## [Unreleased]

### Ajouté
- Composant **sélecteur de dossier natif** dans le navigateur (`components/folder_picker/`) via File System Access API (`showDirectoryPicker`) — aucun ZIP manuel, aucune popup d'import navigateur
- Modal de confirmation personnalisé (nom du dossier, nombre de fichiers) avant envoi à Streamlit
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

### Modifié
- Mode **100 % en ligne** : suppression du mode local tkinter, sélection de dossier via composant HTML dans le navigateur
- Bouton "Lancer l'audit" verrouillé (`audit_en_cours`) pendant toute la durée de l'analyse, avec reset garanti via `try/finally`
- Extraction ZIP via `io.BytesIO` — supprime l'écriture disque intermédiaire
- Streaming O(n) : accumulation par concaténation au lieu de `"".join(chunks)` à chaque chunk
- Import `streamlit` hoissé en singleton module-level dans `settings.py` — exécuté une seule fois
- `MAX_OUTPUT_TOKENS` relevé à 65536 pour garantir la génération des 11 blocs complets
- Remplacement de WeasyPrint (nécessitait GTK3 sur Windows) par ReportLab
- Sidebar Streamlit verrouillée en position ouverte (bouton de repli masqué via CSS)

### Corrigé
- Erreur PDF ReportLab `too large on page` : blocs de code découpés en chunks de 55 lignes max pour tenir dans le frame de page
- `except Exception` trop large dans `_lire_secret` remplacé par `except (AttributeError, KeyError)`
- Rapports illisibles sur Windows : normalisation des fins de ligne (`\r\n` → `\n`)
- Troncature du rapport au BLOC 4 : budget de tokens insuffisant (thinking tokens Gemini non comptés)
- Ingestion du dossier `audit-agent-env/` (venv non standard) : détection générique via `pyvenv.cfg`

### Supprimé
- Dépendance WeasyPrint (remplacée par ReportLab)
- Option CLI `--sortie` (les rapports vont toujours à la racine du projet audité)
- Scripts `lancer.bat` / `lancer.sh` (mode local supprimé, tout se fait en ligne)
- Mode local tkinter (sélecteur de dossier natif OS, sauvegarde dans le projet audité)
