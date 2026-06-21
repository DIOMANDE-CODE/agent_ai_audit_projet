import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

import google.genai as genai  # type: ignore[import-untyped]
from google.genai import types  # type: ignore[import-untyped]
from google.genai.errors import APIError  # type: ignore[import-untyped]
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from config import settings
from core.prompts import SYSTEM_INSTRUCTION

logger = logging.getLogger(__name__)

_MAX_TENTATIVES = 3
_WAIT_MIN = 2
_WAIT_MAX = 30


@dataclass
class AuditResult:
    """Résultat structuré d'un appel à Gemini."""
    contenu: str
    modele: str
    nb_caracteres: int
    duree_secondes: float
    nb_tentatives: int = field(default=1)
    tokens_prompt: int = field(default=0)
    tokens_reponse: int = field(default=0)

    @property
    def tokens_total(self) -> int:
        return self.tokens_prompt + self.tokens_reponse

    def to_dict(self) -> dict:
        return {
            "modele": self.modele,
            "nb_caracteres": self.nb_caracteres,
            "duree_secondes": self.duree_secondes,
            "nb_tentatives": self.nb_tentatives,
            "tokens_prompt": self.tokens_prompt,
            "tokens_reponse": self.tokens_reponse,
            "tokens_total": self.tokens_total,
        }

    def __str__(self) -> str:
        return (
            f"[AuditResult] modèle={self.modele} | "
            f"{self.nb_caracteres} chars | "
            f"{self.duree_secondes:.2f}s | "
            f"{self.nb_tentatives} tentative(s) | "
            f"tokens={self.tokens_total} "
            f"(prompt={self.tokens_prompt}, réponse={self.tokens_reponse})"
        )


class GeminiClientError(Exception):
    """Erreur métier levée par GeminiClient."""


class ReponseVideError(GeminiClientError):
    """Levée quand Gemini retourne une réponse vide ou bloquée par les filtres."""


def _valider_contenu(texte: str) -> None:
    """
    Détecte les réponses dégénérées du modèle (espaces massifs, aucune structure)
    et lève ReponseVideError avant de sauvegarder un fichier inutilisable.
    """
    if len(texte) < 200:
        return  # Trop court pour analyser statistiquement

    ratio_espaces = texte.count(" ") / len(texte)
    nb_newlines = texte.count("\n") + texte.count("\r")

    if ratio_espaces > 0.80:
        raise ReponseVideError(
            f"Réponse dégénérée : {ratio_espaces:.0%} d'espaces ({len(texte):,} chars). "
            "Le modèle s'est bloqué en générant des espaces. Relancez l'audit."
        )

    if len(texte) > 2000 and nb_newlines < 5:
        raise ReponseVideError(
            f"Réponse sans structure : {nb_newlines} retour(s) à la ligne pour {len(texte):,} chars. "
            "Le modèle a généré une seule ligne géante. Relancez l'audit."
        )


class GeminiClient:
    """
    Client professionnel pour l'API Gemini (SDK google-genai).

    Fonctionnalités :
    - Retry automatique (x3) avec backoff exponentiel sur les erreurs API transitoires.
    - Streaming manuel avec retry correct via _appeler_stream_avec_retry().
    - Comptage de tokens (prompt + réponse) dans AuditResult.
    - nb_tentatives réel par appel (pas cumulatif).
    - Logs structurés à chaque étape.
    """

    def __init__(self) -> None:
        self._initialiser_client()
        self.model = settings.MODEL_NAME
        self.temperature = settings.TEMPERATURE
        self.max_output_tokens = settings.MAX_OUTPUT_TOKENS

        logger.info(
            "GeminiClient prêt — modèle=%s | temperature=%.2f | max_tokens=%d",
            self.model,
            self.temperature,
            self.max_output_tokens,
        )

    def _initialiser_client(self) -> None:
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            logger.warning(
                "GEMINI_API_KEY non définie — "
                "le SDK utilisera la variable d'environnement GOOGLE_API_KEY."
            )
            self.client = genai.Client()

    def _construire_config(self) -> types.GenerateContentConfig:
        # thinking_budget plafonne les tokens de raisonnement interne de gemini-2.5-flash,
        # garantissant que le reste du budget max_output_tokens va au texte visible.
        thinking_budget = min(10_000, self.max_output_tokens // 4)
        try:
            return types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
                thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
            )
        except Exception:
            # Fallback si ThinkingConfig n'est pas supporté par la version du SDK
            return types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=self.temperature,
                max_output_tokens=self.max_output_tokens,
            )

    @staticmethod
    def _extraire_tokens(response) -> tuple[int, int]:
        """Extrait le comptage de tokens depuis usage_metadata si disponible."""
        meta = getattr(response, "usage_metadata", None)
        if meta is None:
            return 0, 0
        return (
            getattr(meta, "prompt_token_count", 0) or 0,
            getattr(meta, "candidates_token_count", 0) or 0,
        )

    def _appeler_gemini(self, prompt: str) -> Any:
        """Appel brut à l'API Gemini — séparé pour permettre le retry unitaire."""
        return self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=self._construire_config(),
        )

    def _appeler_gemini_stream(self, prompt: str) -> Any:
        """Appel brut en streaming — séparé pour permettre le retry unitaire."""
        return self.client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=self._construire_config(),
        )

    def analyser_projet(self, prompt: str) -> AuditResult:
        """
        Envoie le prompt d'audit à Gemini et retourne un AuditResult structuré.
        Réessaie automatiquement jusqu'à 3 fois sur erreur API transitoire.

        Args:
            prompt: Le prompt complet généré par generer_prompt_analyse().

        Returns:
            AuditResult contenant le rapport Markdown et les métadonnées d'exécution.

        Raises:
            ReponseVideError: Si Gemini retourne une réponse vide ou bloquée.
            APIError: Si l'API échoue après 3 tentatives.
        """
        debut = time.monotonic()
        nb_tentatives = 0

        @retry(
            retry=retry_if_exception_type(APIError),
            stop=stop_after_attempt(_MAX_TENTATIVES),
            wait=wait_exponential(multiplier=1, min=_WAIT_MIN, max=_WAIT_MAX),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _appel() -> Any:
            nonlocal nb_tentatives
            nb_tentatives += 1
            logger.info(
                "Appel Gemini — modèle=%s | prompt=%d chars | tentative=%d",
                self.model, len(prompt), nb_tentatives,
            )
            try:
                return self._appeler_gemini(prompt)
            except APIError as e:
                logger.error("Erreur API Gemini [%s] : %s", type(e).__name__, e)
                raise GeminiClientError(str(e)) from e

        response = _appel()
        duree = time.monotonic() - debut

        if not response.text:
            raise ReponseVideError(
                "Gemini a retourné une réponse vide ou bloquée par les filtres de sécurité. "
                "Vérifiez la taille du contexte ou les paramètres du modèle."
            )

        _valider_contenu(response.text)

        tokens_prompt, tokens_reponse = self._extraire_tokens(response)

        resultat = AuditResult(
            contenu=response.text,
            modele=self.model,
            nb_caracteres=len(response.text),
            duree_secondes=round(duree, 2),
            nb_tentatives=nb_tentatives,
            tokens_prompt=tokens_prompt,
            tokens_reponse=tokens_reponse,
        )

        logger.info("Réponse reçue — %s", resultat)
        return resultat

    def analyser_projet_stream(self, prompt: str) -> Iterator[str]:
        """
        Variante streaming : yield les chunks de texte au fur et à mesure.
        Le retry porte uniquement sur l'ouverture du stream (avant le premier yield),
        ce qui est sémantiquement correct : on ne peut pas re-yielder des chunks déjà émis.

        Args:
            prompt: Le prompt complet généré par generer_prompt_analyse().

        Yields:
            Chunks de texte Markdown reçus progressivement.

        Raises:
            ReponseVideError: Si aucun chunk n'est reçu.
            GeminiClientError: Sur erreur API non récupérable après 3 tentatives.
        """
        nb_tentatives = 0

        @retry(
            retry=retry_if_exception_type(APIError),
            stop=stop_after_attempt(_MAX_TENTATIVES),
            wait=wait_exponential(multiplier=1, min=_WAIT_MIN, max=_WAIT_MAX),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _ouvrir_stream():
            nonlocal nb_tentatives
            nb_tentatives += 1
            logger.info(
                "Ouverture stream Gemini — modèle=%s | prompt=%d chars | tentative=%d",
                self.model, len(prompt), nb_tentatives,
            )
            try:
                return self._appeler_gemini_stream(prompt)
            except APIError as e:
                logger.error("Erreur API Gemini (stream) : %s", e)
                raise GeminiClientError(str(e)) from e

        stream = _ouvrir_stream()

        nb_chunks = 0
        chunks_accumules: list[str] = []
        for chunk in stream:
            if chunk.text:
                nb_chunks += 1
                chunks_accumules.append(chunk.text)
                yield chunk.text

        if nb_chunks == 0:
            raise ReponseVideError(
                "Le stream Gemini n'a produit aucun chunk. "
                "Vérifiez le modèle et la taille du prompt."
            )

        _valider_contenu("".join(chunks_accumules))

        logger.info(
            "Stream terminé — %d chunks reçus | tentatives=%d",
            nb_chunks, nb_tentatives,
        )
