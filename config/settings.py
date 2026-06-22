import os
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(".env")

# Import streamlit une seule fois ; None si exécuté hors contexte Streamlit.
try:
    import streamlit as _st
except ImportError:
    _st = None  # type: ignore[assignment]


def _lire_secret(cle: str, defaut: str = "") -> str:
    """Lit depuis st.secrets (Streamlit Cloud) en priorité, puis depuis .env / variables d'environnement."""
    if _st is not None:
        try:
            val = _st.secrets.get(cle)
            if val is not None:
                return str(val)
        except Exception:
            pass
    return os.getenv(cle, defaut)


class Settings:
    def __init__(self) -> None:
        self.GEMINI_API_KEY: str    = _lire_secret("GEMINI_API_KEY")
        self.MODEL_NAME: str        = _lire_secret("MODEL_NAME", "gemini-2.5-flash")
        self.TEMPERATURE: float     = float(_lire_secret("TEMPERATURE", "0.1"))
        self.MAX_OUTPUT_TOKENS: int = int(_lire_secret("MAX_OUTPUT_TOKENS", "65536"))

    def valider_configuration(self) -> None:
        if not self.GEMINI_API_KEY:
            raise ValueError(
                "Clé API Gemini non configurée. "
                "Ajoutez GEMINI_API_KEY dans les Secrets de l'application Streamlit Cloud."
            )
