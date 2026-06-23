"""
CLI d'audit technique de projets.
Usage : audit /chemin/vers/mon-projet [--stream]
"""

import argparse
import getpass
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.rule import Rule
from rich.text import Text

from config import settings
from core.ingestion import charger_contexte_projet
from core.prompts import generer_prompt_analyse
from services.gemini_client import GeminiClient, GeminiClientError, ReponseVideError
from services.pdf_generator import generer_pdf

console = Console()


# ── Configuration automatique au premier lancement ───────────────────────────

def _sauvegarder_cle(cle: str) -> Path:
    """Écrit GEMINI_API_KEY dans ~/.env sans écraser les autres variables."""
    env_path = Path.home() / ".env"
    lignes = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    lignes = [l for l in lignes if not l.startswith("GEMINI_API_KEY=")]
    lignes.append(f"GEMINI_API_KEY={cle}")
    env_path.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return env_path


def configurer_si_necessaire() -> None:
    """
    Si aucune clé API n'est trouvée, demande interactivement à l'utilisateur
    de la saisir, la sauvegarde dans ~/.env et recharge les settings.
    Appelé automatiquement au premier `audit`.
    """
    if settings.GEMINI_API_KEY:
        return

    console.print(Rule("[bold yellow]Configuration initiale de CodePulse[/bold yellow]"))
    console.print(
        "\nAucune clé API Gemini trouvée.\n"
        "Obtenez la vôtre gratuitement sur : "
        "[cyan]https://aistudio.google.com/apikey[/cyan]\n"
    )

    while True:
        cle = getpass.getpass("  Entrez votre clé API Gemini : ").strip()
        if cle:
            break
        console.print("  [red]Clé vide — réessayez.[/red]")

    env_path = _sauvegarder_cle(cle)
    load_dotenv(env_path, override=True)
    settings.GEMINI_API_KEY = cle

    console.print(f"\n  [green]✓[/green] Clé sauvegardée dans [cyan]{env_path}[/cyan]")
    console.print("  Elle sera utilisée automatiquement à chaque prochain lancement.\n")
    console.print(Rule(style="dim"))


# ── Sauvegarde ────────────────────────────────────────────────────────────────

def sauvegarder_rapport(contenu: str, chemin_projet: Path, dossier_sortie: Path) -> Path:
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_projet = chemin_projet.resolve().name
    chemin_rapport = dossier_sortie / f"audit_{nom_projet}_{horodatage}.md"
    contenu_normalise = contenu.replace("\r\n", "\n").replace("\r", "\n")
    chemin_rapport.write_text(contenu_normalise, encoding="utf-8", newline="\n")
    return chemin_rapport


# ── Orchestration ─────────────────────────────────────────────────────────────

def lancer_audit(chemin_projet: str, stream: bool) -> int:
    chemin = Path(chemin_projet)
    dossier_sortie = chemin.resolve()

    console.print(Rule("[bold cyan]CodePulse — Audit Technique de Projet[/bold cyan]"))

    # Étape 1 : ingestion
    console.print(f"\n[bold]1/4[/bold] Ingestion du projet : [cyan]{chemin.resolve()}[/cyan]")
    try:
        contexte, metadonnees = charger_contexte_projet(str(chemin))
    except FileNotFoundError as e:
        console.print(f"[bold red]ERREUR :[/bold red] {e}")
        return 1

    nb_fichiers    = metadonnees.get("nb_fichiers", 0)
    nb_ignores     = len(metadonnees.get("fichiers_ignores", []))
    tokens_estimes = metadonnees.get("tokens_estimes", 0)
    chars_contexte = metadonnees.get("chars_contexte", 0)

    console.print(
        f"    [green]✓[/green] {nb_fichiers} fichier(s) chargé(s) — "
        f"{nb_ignores} ignoré(s) — ~{tokens_estimes:,} tokens "
        f"({chars_contexte:,} chars)"
    )

    if nb_fichiers == 0:
        console.print("[bold red]Aucun fichier analysable trouvé dans ce projet.[/bold red]")
        return 1

    # Étape 2 : prompt
    console.print("\n[bold]2/4[/bold] Génération du prompt…")
    prompt = generer_prompt_analyse(contexte, metadonnees)
    console.print(f"    [green]✓[/green] Prompt prêt ({len(prompt):,} caractères)")

    # Étape 3 : Gemini
    client = GeminiClient()

    try:
        if stream:
            console.print("\n[bold]3/4[/bold] Génération du rapport [dim](streaming)[/dim]\n")
            console.print(Rule(style="dim"))
            chunks: list[str] = []
            for chunk in client.analyser_projet_stream(prompt):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print()
            console.print(Rule(style="dim"))
            contenu_rapport = "".join(chunks)
        else:
            console.print("\n[bold]3/4[/bold] Génération du rapport…")
            with console.status("[cyan]Appel à Gemini en cours…[/cyan]", spinner="dots"):
                resultat = client.analyser_projet(prompt)
            contenu_rapport = resultat.contenu
            console.print(f"    [green]✓[/green] {len(contenu_rapport):,} caractères reçus")

    except ReponseVideError as e:
        console.print(f"[bold red]ERREUR :[/bold red] Réponse vide de Gemini : {e}")
        return 1
    except GeminiClientError as e:
        console.print(f"[bold red]ERREUR client Gemini :[/bold red] {e}")
        return 1
    except Exception as e:
        console.print(f"[bold red]ERREUR inattendue :[/bold red] {e}")
        return 1

    # Étape 4 : sauvegarde
    console.print("\n[bold]4/4[/bold] Sauvegarde des rapports…")
    chemin_rapport = sauvegarder_rapport(contenu_rapport, chemin, dossier_sortie)
    console.print(f"    [green]✓[/green] Markdown → [cyan]{chemin_rapport.resolve()}[/cyan]")

    try:
        chemin_pdf = generer_pdf(contenu_rapport, chemin_rapport)
        taille_ko  = chemin_pdf.stat().st_size / 1024
        console.print(f"    [green]✓[/green] PDF ({taille_ko:.0f} Ko) → [cyan]{chemin_pdf.resolve()}[/cyan]")
    except Exception as e:
        console.print(f"    [yellow]⚠[/yellow] PDF non généré : {e}")

    console.print(Rule(style="green"))
    console.print(Text("  Audit terminé.", style="bold green"))
    console.print(Rule(style="green"))
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def construire_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit",
        description="CodePulse — génère un rapport d'audit technique complet d'un projet via Gemini.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
exemples :
  audit /chemin/vers/mon-projet
  audit .
  audit /chemin/vers/mon-projet --stream

Les rapports (.md et .pdf) sont générés à la racine du projet audité.
        """,
    )
    parser.add_argument(
        "projet",
        help="Chemin vers le dossier racine du projet à auditer.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Affiche le rapport en temps réel pendant la génération.",
    )
    return parser


def main() -> None:
    parser = construire_parser()
    args = parser.parse_args()
    configurer_si_necessaire()
    sys.exit(lancer_audit(chemin_projet=args.projet, stream=args.stream))


if __name__ == "__main__":
    main()
