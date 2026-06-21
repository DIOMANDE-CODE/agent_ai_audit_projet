import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from config import settings
from core.ingestion import charger_contexte_projet
from core.prompts import generer_prompt_analyse
from services.gemini_client import GeminiClient, GeminiClientError, ReponseVideError
from services.pdf_generator import generer_pdf

# ── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Sauvegarde ───────────────────────────────────────────────────────────────


def sauvegarder_rapport(
    contenu: str, chemin_projet: Path, dossier_sortie: Path
) -> Path:
    """Sauvegarde le rapport Markdown dans le dossier de sortie."""
    dossier_sortie.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_projet = chemin_projet.resolve().name
    chemin_rapport = dossier_sortie / f"audit_{nom_projet}_{horodatage}.md"
    # Normalise en LF pur pour éviter \r\r\n sur Windows (Python text-mode double les \r)
    contenu_normalise = contenu.replace("\r\n", "\n").replace("\r", "\n")
    chemin_rapport.write_text(contenu_normalise, encoding="utf-8", newline="\n")
    return chemin_rapport


# ── Orchestration principale ──────────────────────────────────────────────────


def lancer_audit(chemin_projet: str, stream: bool) -> int:
    """
    Orchestre les 3 étapes de l'audit :
      1. Ingestion du projet
      2. Génération du prompt
      3. Appel à Gemini + sauvegarde du rapport

    Returns:
        Code de sortie : 0 = succès, 1 = erreur.
    """
    chemin = Path(chemin_projet)
    dossier_sortie = chemin.resolve()  # Rapports déposés à la racine du projet audité

    # ── Étape 0 : validation de la configuration ──────────────────────────
    print("\nValidation de la configuration...")
    try:
        settings.valider_configuration()
    except ValueError as e:
        print(f"\nERREUR de configuration :\n{e}", file=sys.stderr)
        return 1

    # ── Étape 1 : ingestion ───────────────────────────────────────────────
    print(f"\nIngestion du projet : {chemin.resolve()}")
    try:
        contexte, metadonnees = charger_contexte_projet(str(chemin))
    except FileNotFoundError as e:
        print(f"\nERREUR : {e}", file=sys.stderr)
        return 1

    nb_fichiers = metadonnees.get("nb_fichiers", 0)
    nb_ignores = len(metadonnees.get("fichiers_ignores", []))
    tokens_estimes = metadonnees.get("tokens_estimes", 0)
    chars_contexte = metadonnees.get("chars_contexte", 0)
    print(f"   {nb_fichiers} fichier(s) charge(s) — {nb_ignores} ignore(s)")
    print(f"   Contexte : {chars_contexte:,} chars (~{tokens_estimes:,} tokens estimes)")

    if nb_fichiers == 0:
        print(
            "\nAUCUN fichier analysable trouve dans ce projet.\n"
            "   Verifiez le chemin fourni ou les extensions supportees.",
            file=sys.stderr,
        )
        return 1

    # ── Étape 2 : génération du prompt ────────────────────────────────────
    print("\nGeneration du prompt d'audit...")
    prompt = generer_prompt_analyse(contexte, metadonnees)
    print(f"   Prompt pret ({len(prompt):,} caracteres)")

    # ── Étape 3 : appel à Gemini ──────────────────────────────────────────
    client = GeminiClient()

    try:
        if stream:
            print("\nGeneration du rapport en streaming...\n")
            print("-" * 60)
            chunks = []
            for chunk in client.analyser_projet_stream(prompt):
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            print("\n" + "-" * 60)
            contenu_rapport = "".join(chunks)
            resultat_log = f"{len(contenu_rapport):,} caracteres recus"
        else:
            print("\nGeneration du rapport en cours (patientez)...")
            resultat = client.analyser_projet(prompt)
            contenu_rapport = resultat.contenu
            resultat_log = str(resultat)

    except ReponseVideError as e:
        print(f"\nERREUR : Reponse vide de Gemini : {e}", file=sys.stderr)
        return 1
    except GeminiClientError as e:
        print(f"\nERREUR client Gemini : {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Erreur inattendue lors de l'appel a Gemini.")
        print(f"\nERREUR inattendue : {e}", file=sys.stderr)
        return 1

    # ── Étape 4 : sauvegarde Markdown ────────────────────────────────────
    chemin_rapport = sauvegarder_rapport(contenu_rapport, chemin, dossier_sortie)
    print(f"\nRapport Markdown sauvegarde : {chemin_rapport.resolve()}")
    print(f"   {resultat_log}")

    # ── Étape 5 : génération PDF ──────────────────────────────────────────
    print("\nGeneration du rapport PDF...")
    try:
        chemin_pdf = generer_pdf(contenu_rapport, chemin_rapport)
        print(f"Rapport PDF sauvegarde    : {chemin_pdf.resolve()}")
        taille_ko = chemin_pdf.stat().st_size / 1024
        print(f"   Taille : {taille_ko:.0f} Ko\n")
    except ImportError as e:
        print(f"\nAVERTISSEMENT PDF : {e}", file=sys.stderr)
        print("   Le rapport Markdown reste disponible.\n")
    except Exception as e:
        logger.exception("Erreur lors de la generation du PDF.")
        print(f"\nAVERTISSEMENT PDF : generation echouee — {e}", file=sys.stderr)
        print("   Le rapport Markdown reste disponible.\n")

    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────


def construire_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit-agent",
        description="Génère un rapport d'audit technique complet d'un projet via Gemini.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples :
  python main.py /chemin/vers/mon-projet
  python main.py /chemin/vers/mon-projet --stream

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

    print("=" * 60)
    print("       AUDIT TECHNIQUE DE PROJET")
    print("=" * 60)

    code_sortie = lancer_audit(
        chemin_projet=args.projet,
        stream=args.stream,
    )
    sys.exit(code_sortie)


if __name__ == "__main__":
    main()
