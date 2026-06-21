"""
Interface Streamlit pour l'agent d'audit technique de projets.
Lance avec : streamlit run app.py
"""

import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

from config import settings
from core.ingestion import charger_contexte_projet
from core.prompts import generer_prompt_analyse
from services.gemini_client import GeminiClient, GeminiClientError, ReponseVideError
from services.pdf_generator import generer_pdf

# ── Configuration de la page ──────────────────────────────────────────────────

st.set_page_config(
    page_title="Audit Project Agent",
    page_icon="assets/icon.png" if Path("assets/icon.png").exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Masque le bouton de repli pour verrouiller la sidebar en position ouverte
st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    section[data-testid="stSidebar"] { pointer-events: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Agent IA d'Audit")

    config_ok = True
    try:
        settings.valider_configuration()
    except ValueError as e:
        st.error(str(e))
        config_ok = False

    st.divider()

    sauvegarder_projet = st.checkbox(
        "Sauvegarder les rapports dans le projet audité",
        value=True,
        help="Stocker les fichiers du rapport à la racine du projet audité.",
    )

# ── Titre principal ───────────────────────────────────────────────────────────

st.title("Agent IA d'Audit Technique de Projets")
st.caption(
    "Obtenez un diagnostic complet de votre projet en quelques minutes — "
    "architecture, sécurite, performance, dépendances et bien plus. "
    "Un rapport professionnel structuré en 11 blocs téléchargeable."
)

if not config_ok:
    st.warning(
        "Configurez votre cle API dans le fichier `.env` avant de lancer un audit.\n\n"
        "Exemple : `GEMINI_API_KEY=votre_cle_ici`"
    )
    st.stop()

# ── Formulaire ────────────────────────────────────────────────────────────────

chemin_saisi = st.text_input(
    "Chemin absolu du projet à auditer",
    placeholder="C:/Users/moi/MonProjet  ou  /home/user/mon-projet",
)

col1, col2 = st.columns([1, 4])
lancer = col1.button("Lancer l'audit", type="primary", use_container_width=True)

if not lancer:
    st.stop()

# ── Validation du chemin ──────────────────────────────────────────────────────

chemin = Path(chemin_saisi.strip()) if chemin_saisi.strip() else None

if not chemin:
    st.error("Veuillez renseigner un chemin de projet.")
    st.stop()

if not chemin.is_dir():
    st.error(f"Chemin introuvable ou n'est pas un dossier : `{chemin}`")
    st.stop()

# ── Pipeline d'audit ──────────────────────────────────────────────────────────

horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
nom_projet = chemin.resolve().name
nom_fichier_base = f"audit_{nom_projet}_{horodatage}"

# Etape 1 — Ingestion
with st.status("Ingestion du projet...", expanded=False) as statut_ingestion:
    try:
        contexte, metadonnees = charger_contexte_projet(str(chemin))
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    nb_fichiers = metadonnees.get("nb_fichiers", 0)
    nb_ignores = len(metadonnees.get("fichiers_ignores", []))
    tokens_estimes = metadonnees.get("tokens_estimes", 0)
    chars_contexte = metadonnees.get("chars_contexte", 0)

    st.write(f"{nb_fichiers} fichier(s) charge(s) — {nb_ignores} ignore(s)")
    st.write(f"Contexte : {chars_contexte:,} chars (~{tokens_estimes:,} tokens estimes)")

    if nb_fichiers == 0:
        st.error("Aucun fichier analysable trouve dans ce projet.")
        st.stop()

    statut_ingestion.update(
        label=f"Ingestion terminee — {nb_fichiers} fichiers / ~{tokens_estimes:,} tokens",
        state="complete",
    )

# Etape 2 — Generation du prompt
with st.status("Generation du prompt d'audit...", expanded=False) as statut_prompt:
    prompt = generer_prompt_analyse(contexte, metadonnees)
    statut_prompt.update(
        label=f"Prompt pret — {len(prompt):,} caracteres",
        state="complete",
    )

# Etape 3 — Appel Gemini en streaming
st.subheader("Rapport d'audit")

rapport_placeholder = st.empty()
client = GeminiClient()
chunks: list[str] = []

try:
    with st.status("Communication avec Gemini en cours...", expanded=False) as statut_gemini:
        for chunk in client.analyser_projet_stream(prompt):
            chunks.append(chunk)
            rapport_placeholder.markdown("".join(chunks))
        statut_gemini.update(
            label=f"Rapport genere — {len(''.join(chunks)):,} caracteres",
            state="complete",
        )
except ReponseVideError as e:
    st.error(f"Reponse invalide de Gemini : {e}")
    st.stop()
except GeminiClientError as e:
    st.error(f"Erreur API Gemini : {e}")
    st.stop()
except Exception as e:
    st.error(f"Erreur inattendue : {e}")
    st.stop()

contenu_rapport = "".join(chunks)
contenu_normalise = contenu_rapport.replace("\r\n", "\n").replace("\r", "\n")

# Etape 4 — Generation du PDF
pdf_bytes: bytes | None = None

with st.status("Generation du rapport PDF...", expanded=False) as statut_pdf:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_md = Path(tmpdir) / f"{nom_fichier_base}.md"
            tmp_md.write_text(contenu_normalise, encoding="utf-8", newline="\n")
            chemin_pdf = generer_pdf(contenu_normalise, tmp_md)
            pdf_bytes = chemin_pdf.read_bytes()
        statut_pdf.update(
            label=f"PDF genere — {len(pdf_bytes) // 1024} Ko",
            state="complete",
        )
    except ImportError as e:
        statut_pdf.update(label=f"PDF non disponible : {e}", state="error")
    except Exception as e:
        statut_pdf.update(label=f"Erreur PDF : {e}", state="error")

# Etape 5 — Sauvegarde dans le projet audite (optionnel)
if sauvegarder_projet:
    with st.status("Sauvegarde dans le projet audite...", expanded=False) as statut_save:
        try:
            chemin_md_sortie = chemin.resolve() / f"{nom_fichier_base}.md"
            chemin_md_sortie.write_text(contenu_normalise, encoding="utf-8", newline="\n")
            saved_paths = [str(chemin_md_sortie)]

            if pdf_bytes:
                chemin_pdf_sortie = chemin.resolve() / f"{nom_fichier_base}.pdf"
                chemin_pdf_sortie.write_bytes(pdf_bytes)
                saved_paths.append(str(chemin_pdf_sortie))

            statut_save.update(
                label="Fichiers sauvegardes dans le projet audite",
                state="complete",
            )
            for p in saved_paths:
                st.write(p)
        except OSError as e:
            statut_save.update(label=f"Erreur de sauvegarde : {e}", state="error")

# ── Boutons de telechargement ─────────────────────────────────────────────────

st.divider()
col_md, col_pdf, _ = st.columns([1, 1, 3])

col_md.download_button(
    label="Telecharger le rapport (.md)",
    data=contenu_normalise.encode("utf-8"),
    file_name=f"{nom_fichier_base}.md",
    mime="text/markdown",
    use_container_width=True,
)

if pdf_bytes:
    col_pdf.download_button(
        label="Telecharger le rapport (.pdf)",
        data=pdf_bytes,
        file_name=f"{nom_fichier_base}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
