# CodePulse — Agent IA d'audit technique de projets

Analysez n'importe quel projet informatique en une commande. CodePulse ingère votre code source, l'envoie à **Google Gemini 2.5 Flash** et génère un rapport structuré en **Markdown et PDF**.

---

## Installation

```bash
pip install agent-audit-ai
```

Aucune configuration requise — la clé API est embarquée dans le package.

---

## Utilisation

```bash
# Auditer le dossier courant
audit .

# Auditer un projet spécifique
audit /chemin/vers/mon-projet

# Afficher le rapport en temps réel
audit /chemin/vers/mon-projet --stream
```

Les rapports `.md` et `.pdf` sont générés à la racine du projet audité.

---

## Ce qui est analysé

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

Le rapport est structuré en **11 blocs d'analyse** avec badges de niveau de risque (CRITIQUE, ÉLEVÉ, MOYEN, FAIBLE, INFO).

---

## Fonctionnalités

- **Clé API embarquée** — aucune configuration après installation
- **Rapport PDF stylisé** — couleurs, badges de risque, mise en page professionnelle
- **Streaming** — affichage en temps réel pendant la génération
- **Ingestion intelligente** — priorité aux fichiers critiques, exclusion automatique de `.env`, `node_modules`, `__pycache__`, venvs…
- **Compatible tous terminaux** — CMD, PowerShell, bash, zsh

---

## Version web (sans installation)

Pour les non-développeurs, une interface web est disponible directement dans le navigateur — aucune installation requise.

**[audit-my-software.onrender.com](https://audit-my-software.onrender.com/)**

---

## Compatibilité

- Python 3.12+
- Windows, macOS, Linux

---

## Liens

- [Code source & documentation](https://github.com/DIOMANDE-CODE/audit-project-agent)
- [Signaler un problème](https://github.com/DIOMANDE-CODE/audit-project-agent/issues)

---

Développé par **DIOMANDE DROH MARTIAL** — Licence MIT
