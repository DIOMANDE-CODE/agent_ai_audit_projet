import os
from pathlib import Path

from dotenv import load_dotenv

# Cherche .env dans le CWD d'abord, puis dans ~ (pour usage CLI depuis n'importe où)
for _env_path in [Path(".env"), Path.home() / ".env"]:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

# Import streamlit une seule fois ; None si exécuté hors contexte Streamlit.
try:
    import streamlit as _st
except ImportError:
    _st = None  # type: ignore[assignment]


def _lire_secret(cle: str, defaut: str = "") -> str:
    """
    Ordre de priorité :
      1. st.secrets       (Streamlit Cloud)
      2. .env / variables d'environnement système
      3. config/_bundled  (clé embarquée dans le package distribué)
    """
    if _st is not None:
        try:
            val = _st.secrets.get(cle)
            if val is not None:
                return str(val)
        except Exception:
            pass

    valeur = os.getenv(cle, "")
    if valeur:
        return valeur

    # Fallback : clé embarquée dans le package (pour les installations distribuées)
    if cle == "GEMINI_API_KEY":
        try:
            from config._bundled import GEMINI_API_KEY as _cle_bundled
            if _cle_bundled:
                return _cle_bundled
        except ImportError:
            pass

    return defaut


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
