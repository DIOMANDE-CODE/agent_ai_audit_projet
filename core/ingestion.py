import os
from typing import Any

# ── Limites de budget ─────────────────────────────────────────────────────────

TAILLE_MAX_FICHIER = 100 * 1024   # 100 Ko par fichier (was 500 Ko)
TAILLE_MAX_CONTEXTE = 400_000     # ~100 000 tokens input max au total
LIGNES_DEBUT_TRONQUE = 250        # Premières lignes conservées lors d'une troncature
LIGNES_FIN_TRONQUE = 50           # Dernières lignes conservées lors d'une troncature

# ── Extensions et fichiers cibles ─────────────────────────────────────────────

EXTENSIONS_CIBLES = (
    # Web — JS / TS
    '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
    # Web — Templates
    '.html', '.htm', '.vue', '.svelte', '.astro',
    # Styles (faible valeur pour l'audit, inclus en dernier)
    '.css', '.scss', '.sass', '.less',
    # Python
    '.py', '.pyw',
    # C / C++
    '.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx',
    # C# / .NET
    '.cs', '.csproj', '.sln', '.razor', '.cshtml',
    # Java / Kotlin / Scala
    '.java', '.kt', '.kts', '.scala', '.groovy',
    # PHP
    '.php',
    # Ruby
    '.rb', '.erb',
    # Go
    '.go',
    # Rust
    '.rs',
    # Swift / Objective-C (iOS / macOS)
    '.swift', '.m', '.mm', '.xcconfig',
    # Dart / Flutter
    '.dart',
    # Elixir
    '.ex', '.exs',
    # Lua
    '.lua',
    # R (data science)
    '.r',
    # Perl
    '.pl', '.pm',
    # Scripts
    '.sh', '.bash', '.zsh', '.ps1', '.bat', '.cmd',
    # Schemas / Protocoles
    '.proto', '.graphql', '.gql', '.prisma',
    # Config / Infra
    '.json', '.json5', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf',
    '.tf', '.tfvars', '.hcl',
    '.xml',
    '.sql', '.env.example',
    # Data science
    '.ipynb',
    # Docs (faible valeur, inclus en dernier)
    '.md', '.rst', '.txt',
)

FICHIERS_SPECIFIQUES = {
    # Conteneurs / Build
    'Dockerfile', 'Makefile', 'CMakeLists.txt', 'Procfile',
    # Python
    'requirements.txt', 'requirements-dev.txt', 'pyproject.toml',
    'setup.py', 'setup.cfg', 'Pipfile', 'tox.ini',
    # JS / Node
    'package.json', '.nvmrc', '.node-version',
    # Go (go.sum exclu — volumineux et peu utile pour l'audit)
    'go.mod',
    # Java / JVM
    'pom.xml', 'build.gradle', 'build.gradle.kts', 'settings.gradle', 'settings.gradle.kts',
    # Rust
    'Cargo.toml',
    # PHP
    'composer.json',
    # Ruby
    'Gemfile', '.ruby-version',
    # Flutter / Dart
    'pubspec.yaml',
    # iOS / macOS
    'Podfile', 'Package.swift',
    # Android
    'AndroidManifest.xml', 'google-services.json',
    # Elixir
    'mix.exs',
    # Infra / Cloud
    'nginx.conf', 'apache.conf', '.env.example',
    # Monorepo
    'lerna.json', 'nx.json', 'turbo.json', 'pnpm-workspace.yaml',
}

DOSSIERS_A_IGNORER = {
    # JS / Node
    'node_modules', '.next', '.nuxt', '.svelte-kit', '.astro',
    # Python
    '.venv', 'venv', 'env', '__pycache__', '.pytest_cache', 'htmlcov', '.mypy_cache', '.ruff_cache',
    # Build / Output
    'dist', 'build', 'out', 'output', 'release', 'bin', 'obj',
    # Java / JVM
    'target', '.gradle',
    # Mobile
    '.dart_tool', 'ios/Pods', 'android/.gradle', 'android/build',
    # Rust
    'target',
    # PHP
    'vendor',
    # Ruby
    '.bundle',
    # Version control
    '.git',
    # IDE
    '.idea', '.vscode', '.eclipse',
    # Assets / médias
    'media', 'staticfiles', 'public/uploads', 'storage',
    # Divers
    'logs', 'tmp', 'temp', 'cache', 'coverage', 'vdoc',
}

FICHIERS_A_IGNORER = {
    # Secrets
    '.env',
    # Locks — volumineux, redondants avec les manifests
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock',
    'Pipfile.lock', 'Gemfile.lock', 'Cargo.lock', 'composer.lock', 'pubspec.lock',
    'go.sum',
    # Système
    '.DS_Store', 'Thumbs.db', 'desktop.ini',
}

# ── Pré-calculs pour éviter les sets reconstruits à chaque itération ──────────

_FICHIERS_SPECIFIQUES_LC: frozenset[str] = frozenset(f.lower() for f in FICHIERS_SPECIFIQUES)

# Extensions à faible valeur pour l'audit de code (docs, styles)
_EXTENSIONS_BASSE_PRIORITE: frozenset[str] = frozenset({
    '.md', '.rst', '.txt', '.css', '.scss', '.sass', '.less',
})


# ── Fonctions utilitaires ─────────────────────────────────────────────────────

def _priorite_fichier(nom: str, ext: str) -> int:
    """
    Retourne le niveau de priorité d'inclusion (0 = le plus urgent).

    0 — manifests & configs clés (package.json, Dockerfile, pyproject.toml, …)
    1 — code source (py, ts, js, java, go, …)
    2 — docs & styles (md, css, scss, …) — inclus en dernier si budget restant
    """
    if nom.lower() in _FICHIERS_SPECIFIQUES_LC:
        return 0
    if ext.lower() in _EXTENSIONS_BASSE_PRIORITE:
        return 2
    return 1


def _tronquer_si_necessaire(contenu: str) -> str:
    """
    Tronque les gros fichiers en gardant le début et la fin.
    Insère un marqueur explicite pour indiquer la portion omise.
    """
    lignes = contenu.splitlines()
    seuil = LIGNES_DEBUT_TRONQUE + LIGNES_FIN_TRONQUE
    if len(lignes) <= seuil:
        return contenu

    omises = len(lignes) - seuil
    marqueur = f"\n[... {omises} lignes omises — troncature automatique pour optimiser les tokens ...]\n"
    return "\n".join(lignes[:LIGNES_DEBUT_TRONQUE]) + marqueur + "\n".join(lignes[-LIGNES_FIN_TRONQUE:])


# ── Fonction principale ───────────────────────────────────────────────────────

def charger_contexte_projet(chemin_projet: str) -> tuple[str, dict[str, Any]]:
    """
    Parcourt le dossier du projet cible et extrait le contenu des fichiers clés,
    en appliquant une stratégie de priorisation et de budget tokens.

    Stratégie d'inclusion :
    - Priorité 0 : manifests et configs clés (toujours inclus en premier)
    - Priorité 1 : code source
    - Priorité 2 : docs et styles (inclus en dernier si budget restant)
    - Troncature automatique pour les fichiers > LIGNES_DEBUT_TRONQUE + LIGNES_FIN_TRONQUE lignes
    - Budget total : TAILLE_MAX_CONTEXTE caractères (~100 000 tokens)

    Args:
        chemin_projet: Chemin absolu ou relatif vers le dossier racine du projet.

    Returns:
        Tuple (contexte_str, metadonnees) où metadonnees contient :
        - 'nb_fichiers' (int)
        - 'fichiers_ignores' (list[tuple[str, str]])
        - 'chars_contexte' (int) — taille totale du contexte généré
        - 'tokens_estimes' (int) — estimation tokens (chars / 4)

    Raises:
        FileNotFoundError: Si le chemin spécifié n'existe pas.
    """
    if not os.path.exists(chemin_projet):
        raise FileNotFoundError(f"Le chemin spécifié n'existe pas : {chemin_projet}")

    candidats: list[tuple[int, int, str, str]] = []  # (priorite, taille, chemin_complet, chemin_relatif)
    fichiers_ignores: list[tuple[str, str]] = []

    # ── Phase 1 : collecte et filtrage ───────────────────────────────────────
    for racine, dirs, fichiers in os.walk(chemin_projet):
        # Exclut les dossiers explicitement ignorés, les dossiers cachés,
        # et les environnements virtuels Python (détectés via pyvenv.cfg).
        def _est_venv(nom: str) -> bool:
            return os.path.isfile(os.path.join(racine, nom, 'pyvenv.cfg'))

        dirs[:] = [
            d for d in dirs
            if d not in DOSSIERS_A_IGNORER
            and not d.startswith('.')
            and not _est_venv(d)
        ]

        for fichier in fichiers:
            if fichier in FICHIERS_A_IGNORER or fichier.startswith('.'):
                continue

            _, ext = os.path.splitext(fichier)
            est_extension_valide = fichier.endswith(EXTENSIONS_CIBLES)
            est_fichier_specifique = fichier.lower() in _FICHIERS_SPECIFIQUES_LC

            if not (est_extension_valide or est_fichier_specifique):
                continue

            chemin_complet = os.path.join(racine, fichier)
            chemin_relatif = os.path.relpath(chemin_complet, chemin_projet)

            taille = os.path.getsize(chemin_complet)
            if taille > TAILLE_MAX_FICHIER:
                fichiers_ignores.append((chemin_relatif, f"trop volumineux ({taille // 1024} Ko > {TAILLE_MAX_FICHIER // 1024} Ko)"))
                continue

            priorite = _priorite_fichier(fichier, ext)
            candidats.append((priorite, taille, chemin_complet, chemin_relatif))

    # ── Phase 2 : tri par priorité puis taille (petits fichiers en premier) ──
    candidats.sort(key=lambda x: (x[0], x[1]))

    # ── Phase 3 : inclusion dans la limite de budget ──────────────────────────
    contexte_complet: list[str] = []
    nb_fichiers = 0
    chars_total = 0

    for priorite, _, chemin_complet, chemin_relatif in candidats:
        if chars_total >= TAILLE_MAX_CONTEXTE:
            fichiers_ignores.append((chemin_relatif, f"budget contexte atteint ({TAILLE_MAX_CONTEXTE // 1000} Ko max)"))
            continue

        try:
            with open(chemin_complet, 'r', encoding='utf-8', errors='ignore') as f:
                contenu = f.read()

            contenu = _tronquer_si_necessaire(contenu)

            taille_bloc = len(contenu) + len(chemin_relatif) * 2 + 40  # overhead des marqueurs
            if chars_total + taille_bloc > TAILLE_MAX_CONTEXTE and nb_fichiers > 0:
                fichiers_ignores.append((chemin_relatif, "budget contexte atteint"))
                continue

            contexte_complet.append(f"=== DEBUT FICHIER: {chemin_relatif} ===")
            contexte_complet.append(contenu)
            contexte_complet.append(f"=== FIN FICHIER: {chemin_relatif} ===\n")
            nb_fichiers += 1
            chars_total += taille_bloc

        except OSError as e:
            fichiers_ignores.append((chemin_relatif, str(e)))

    metadonnees: dict[str, Any] = {
        "nb_fichiers": nb_fichiers,
        "fichiers_ignores": fichiers_ignores,
        "chars_contexte": chars_total,
        "tokens_estimes": chars_total // 4,
    }

    return "\n".join(contexte_complet), metadonnees
