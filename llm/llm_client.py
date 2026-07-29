"""Client LLM à backend interchangeable : Google Gemini (par défaut) ou tout
serveur compatible OpenAI (vLLM, llama.cpp, Ollama, LM Studio…). Le choix se
fait via LLM_PROVIDER dans la configuration."""
import requests
from google import genai

from config import (
    DEMO_MODE,
    LLM_NO_THINK,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    require_gemini_key,
)
from llm.prompt_templates import system_prompt

DEFAULT_MODEL = "gemini-3.5-flash"
_OPENAI_TIMEOUT = 120

_client: genai.Client | None = None


class LLMQuotaError(RuntimeError):
    """Quota/rate limit du fournisseur LLM dépassé (HTTP 429)."""


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=require_gemini_key())
    return _client


def _generate_openai(prompt: str, lang: str) -> str:
    """Génération via un endpoint compatible OpenAI (/v1/chat/completions)."""
    if not OPENAI_BASE_URL or not OPENAI_MODEL:
        raise RuntimeError(
            "LLM_PROVIDER=openai mais OPENAI_BASE_URL ou OPENAI_MODEL manquant dans .env."
        )
    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt(lang)},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    if LLM_NO_THINK:
        # Désactive la phase de « réflexion » des modèles à raisonnement (Qwen3…)
        # pour ne pas renvoyer un contenu vide ; ignoré par les serveurs qui ne
        # la connaissent pas.
        body["chat_template_kwargs"] = {"enable_thinking": False}

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"} if OPENAI_API_KEY else {}
    try:
        resp = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions", json=body, headers=headers, timeout=_OPENAI_TIMEOUT
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Échec réseau vers le LLM compatible OpenAI: {exc}") from exc

    if resp.status_code == 429:
        raise LLMQuotaError("Quota du LLM dépassé (429).")
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur HTTP {resp.status_code} du LLM: {resp.text[:300]}")

    content = (resp.json()["choices"][0]["message"].get("content") or "").strip()
    if not content:
        raise RuntimeError("Le LLM a renvoyé une réponse vide.")
    return content


def generate_report(prompt: str, model: str = DEFAULT_MODEL, lang: str = "fr") -> str:
    """Envoie un prompt au LLM avec le système strict anti-hallucination et renvoie le texte.

    `lang` ("fr"/"en") choisit la langue de sortie via le prompt système ; les
    templates métier restent en français (ce sont des instructions).

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

    if LLM_PROVIDER == "openai":
        return _generate_openai(prompt, lang)

    client = _get_client()
    try:
        interaction = client.interactions.create(
            model=model,
            system_instruction=system_prompt(lang),
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
