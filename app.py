"""
Interface Streamlit pour l'agent d'audit technique de projets.
Lance avec : streamlit run app.py
"""

import base64
import io
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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

st.markdown(
    """
    <style>
    [data-testid="collapsedControl"] { display: none; }
    h1 { font-size: 2rem !important; font-weight: 700 !important; }
    div[data-testid="stButton"] > button[kind="primary"] {
        height: 2.8rem; font-size: 1rem; font-weight: 600;
    }
    div[data-testid="stDownloadButton"] > button {
        border-radius: 8px; font-weight: 600;
    }
    div[data-testid="stStatus"] { margin-bottom: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Composant sélecteur de dossier ────────────────────────────────────────────

_COMPONENT_DIR = Path(__file__).parent / "components" / "folder_picker"
_folder_picker = components.declare_component("folder_picker", path=str(_COMPONENT_DIR))

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## Agent IA d'Audit")

    config_ok = True
    try:
        settings.valider_configuration()
    except ValueError as e:
        st.error(str(e))
        config_ok = False

    if config_ok:
        st.success("Service opérationnel")

    st.divider()

    st.markdown(
        "Cet agent analyse automatiquement votre code source et génère "
        "un rapport professionnel structuré en **11 blocs d'analyse**."
    )

    st.markdown("""
**Ce qui est analysé :**
- Architecture & structure
- Qualité du code
- Sécurité & vulnérabilités
- Performance
- Dépendances & librairies
- Tests & couverture
- Documentation
- Maintenabilité
    """)

    st.divider()
    st.caption("Fait par DIOMANDE DROH MARTIAL")

# ── Titre principal ───────────────────────────────────────────────────────────

st.title("Audit Technique de Projets")
st.markdown(
    "Obtenez un diagnostic complet de votre code en quelques minutes — "
    "architecture, sécurité, performance et bien plus. "
    "Rapport structuré disponible en Markdown et PDF."
)

if not config_ok:
    st.stop()

st.divider()

# ── Zone de sélection du projet ───────────────────────────────────────────────

if "audit_en_cours" not in st.session_state:
    st.session_state.audit_en_cours = False

with st.container(border=True):
    st.markdown("#### Sélectionnez votre projet")
    st.caption(
        "Choisissez le dossier racine de votre projet. "
        "Les fichiers sensibles (.env, node_modules, __pycache__…) sont automatiquement exclus."
    )

    b64_zip: str | None = _folder_picker(key="folder_picker", default=None, height=240)

    st.markdown("")

    btn_label = "Analyse en cours..." if st.session_state.audit_en_cours else "Lancer l'audit"
    lancer = st.button(
        btn_label,
        type="primary",
        disabled=b64_zip is None or st.session_state.audit_en_cours,
        use_container_width=True,
    )

if lancer:
    st.session_state.audit_en_cours = True

if not lancer and not st.session_state.audit_en_cours:
    st.stop()

if not b64_zip:
    st.error("Veuillez sélectionner un dossier avant de lancer l'audit.")
    st.stop()

st.divider()

# ── Pipeline d'audit ──────────────────────────────────────────────────────────

tmpdir_zip: tempfile.TemporaryDirectory | None = None  # type: ignore[type-arg]

try:
    # Extraction du ZIP (BytesIO — pas d'écriture disque intermédiaire)
    with st.status("Chargement du projet...", expanded=False) as statut_zip:
        try:
            zip_buffer = io.BytesIO(base64.b64decode(b64_zip))
            tmpdir_zip = tempfile.TemporaryDirectory()

            with zipfile.ZipFile(zip_buffer, "r") as zf:
                membres_surs = [
                    m for m in zf.namelist()
                    if not m.startswith("/") and ".." not in m
                ]
                zf.extractall(tmpdir_zip.name, members=membres_surs)

            contenu = [
                p for p in Path(tmpdir_zip.name).iterdir()
                if not p.name.startswith(".")
            ]
            chemin = (
                contenu[0]
                if len(contenu) == 1 and contenu[0].is_dir()
                else Path(tmpdir_zip.name)
            )
            statut_zip.update(label=f"Projet chargé — {chemin.name}", state="complete")

        except Exception as e:
            st.error(f"Erreur lors du chargement du projet : {e}")
            st.stop()

    horodatage     = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_projet     = chemin.resolve().name
    nom_fichier_base = f"audit_{nom_projet}_{horodatage}"

    # Ingestion + génération du prompt
    with st.status("Analyse du projet...", expanded=False) as statut_ingestion:
        try:
            contexte, metadonnees = charger_contexte_projet(str(chemin))
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()

        nb_fichiers    = metadonnees.get("nb_fichiers", 0)
        nb_ignores     = len(metadonnees.get("fichiers_ignores", []))
        tokens_estimes = metadonnees.get("tokens_estimes", 0)

        if nb_fichiers == 0:
            st.error("Aucun fichier analysable trouvé dans ce projet.")
            st.stop()

        prompt = generer_prompt_analyse(contexte, metadonnees)
        statut_ingestion.update(
            label=f"{nb_fichiers} fichiers analysés — {nb_ignores} ignorés — ~{tokens_estimes:,} tokens",
            state="complete",
        )

    # Rapport en streaming (accumulation O(n) au lieu de join O(n²) par chunk)
    st.markdown("### Rapport d'audit")
    rapport_placeholder = st.empty()
    client = GeminiClient()
    rapport_accumule = ""

    try:
        with st.status("Génération du rapport en cours...", expanded=False) as statut_gemini:
            for chunk in client.analyser_projet_stream(prompt):
                rapport_accumule += chunk
                rapport_placeholder.markdown(rapport_accumule)
            statut_gemini.update(
                label=f"Rapport généré — {len(rapport_accumule):,} caractères",
                state="complete",
            )
    except ReponseVideError as e:
        st.error(f"Réponse invalide de l'IA : {e}")
        st.stop()
    except GeminiClientError as e:
        st.error(f"Erreur API : {e}")
        st.stop()
    except Exception as e:
        st.error(f"Erreur inattendue : {e}")
        st.stop()

    contenu_normalise = rapport_accumule.replace("\r\n", "\n").replace("\r", "\n")

    # Génération du PDF
    pdf_bytes: bytes | None = None
    with st.status("Génération du PDF...", expanded=False) as statut_pdf:
        try:
            with tempfile.TemporaryDirectory() as tmpdir_pdf:
                tmp_md = Path(tmpdir_pdf) / f"{nom_fichier_base}.md"
                tmp_md.write_text(contenu_normalise, encoding="utf-8", newline="\n")
                chemin_pdf = generer_pdf(contenu_normalise, tmp_md)
                pdf_bytes = chemin_pdf.read_bytes()
            statut_pdf.update(
                label=f"PDF prêt — {len(pdf_bytes) // 1024} Ko",
                state="complete",
            )
        except Exception as e:
            statut_pdf.update(label=f"Erreur PDF : {e}", state="error")

finally:
    # Garanti même si st.stop() est appelé en cours de pipeline
    if tmpdir_zip is not None:
        tmpdir_zip.cleanup()
    st.session_state.audit_en_cours = False

# ── Téléchargements ───────────────────────────────────────────────────────────

st.divider()
st.markdown("#### Télécharger le rapport")

col_md, col_pdf, _ = st.columns([1, 1, 2])

with col_md:
    st.download_button(
        label="Rapport Markdown (.md)",
        data=contenu_normalise.encode("utf-8"),
        file_name=f"{nom_fichier_base}.md",
        mime="text/markdown",
        use_container_width=True,
    )

if pdf_bytes:
    with col_pdf:
        st.download_button(
            label="Rapport PDF (.pdf)",
            data=pdf_bytes,
            file_name=f"{nom_fichier_base}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
