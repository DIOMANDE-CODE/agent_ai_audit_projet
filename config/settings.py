import os
import warnings
from dotenv import load_dotenv

if os.path.exists(".env"):
    load_dotenv(".env")
else:
    warnings.warn(
        "Fichier .env non trouvé. Les variables d'environnement doivent être définies manuellement.",
        stacklevel=1,
    )


class Settings:
    def __init__(self) -> None:
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
        self.TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
        self.MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "65536"))

    def valider_configuration(self) -> None:
        manquantes = []
        if not self.GEMINI_API_KEY:
            manquantes.append("GEMINI_API_KEY")
        if not self.MODEL_NAME:
            manquantes.append("MODEL_NAME")
        if manquantes:
            raise ValueError(
                f"Variables d'environnement manquantes : {', '.join(manquantes)}\n"
                "Veuillez les définir dans un fichier .env à la racine du projet."
            )