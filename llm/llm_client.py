"""Wrapper minimal autour du SDK Google Gemini (google-genai) pour la génération de rapports."""
from google import genai

from config import DEMO_MODE, require_gemini_key
from llm.prompt_templates import SYSTEM_PROMPT

DEFAULT_MODEL = "gemini-3.5-flash"

_client: genai.Client | None = None


class LLMQuotaError(RuntimeError):
    """Quota/rate limit Gemini dépassé (HTTP 429)."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=require_gemini_key())
    return _client


def generate_report(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Envoie un prompt au LLM avec le système strict anti-hallucination et renvoie le texte.

    Toute erreur du SDK google-genai est convertie ici en RuntimeError : le SDK
    expose plusieurs hiérarchies d'exceptions internes selon l'API utilisée
    (dont certaines dans des modules privés `_gaos`), donc on détecte le 429
    par attribut (`status_code`/`code`) plutôt que par import de classe privée.
    """
    if DEMO_MODE:
        # RuntimeError est déjà traduit en 503 par les routers /report et
        # /player : le rapport non caché est simplement indisponible.
        raise RuntimeError(
            "Mode démo : seuls les rapports déjà générés sont consultables. "
            "La génération LLM est désactivée sur cette instance publique."
        )

    client = _get_client()
    try:
        interaction = client.interactions.create(
            model=model,
            system_instruction=SYSTEM_PROMPT,
            input=prompt,
        )
    except Exception as exc:
        status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        if status_code == 429:
            raise LLMQuotaError(
                "Quota Gemini dépassé (429). Réessaie plus tard ou vérifie ton plan sur "
                "https://aistudio.google.com/."
            ) from exc
        raise RuntimeError(f"Erreur lors de l'appel au LLM Gemini: {exc}") from exc

    return interaction.output_text
