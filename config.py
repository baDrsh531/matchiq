"""Chargement centralisé de la configuration depuis .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_BASE_URL = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Backend LLM interchangeable. "gemini" (défaut) utilise l'API Google ; "openai"
# cible tout serveur compatible OpenAI (vLLM, llama.cpp, Ollama, LM Studio, ou
# l'API OpenAI elle-même) — utile pour un modèle local, hors quota. L'URL et le
# modèle restent dans .env (jamais commités).
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Certains modèles « à raisonnement » (Qwen3, etc.) consomment tout le budget de
# tokens dans une phase de réflexion et renvoient un contenu vide : on désactive
# ce mode par défaut côté serveurs qui le supportent (chat_template_kwargs).
LLM_NO_THINK = os.getenv("LLM_NO_THINK", "true").strip().lower() in {"1", "true", "yes", "on"}

# Mode démo : l'application ne sert QUE les données déjà en cache (data/raw,
# data/processed, SQLite) et refuse tout appel sortant vers API-Football ou
# Gemini. Permet d'exposer une instance publique sans clé, sans quota
# consommable et sans facture possible, quoi que fasse un visiteur.
DEMO_MODE = os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}

# Répertoire des données (cache brut, rapports, base SQLite). Configurable pour
# que la démo publique pointe vers `demo_data/` — un jeu réduit et versionné —
# au lieu de `data/`, qui est gitignoré et contient le cache de travail local.
DATA_DIR = Path(os.getenv("DATA_DIR") or (BASE_DIR / "data"))
if not DATA_DIR.is_absolute():
    DATA_DIR = BASE_DIR / DATA_DIR

_DEFAULT_DB_PATH = DATA_DIR / "matchiq.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB_PATH}")

DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

_REQUIRED = {
    "API_FOOTBALL_KEY": API_FOOTBALL_KEY,
}


def require_api_football_key() -> str:
    if not API_FOOTBALL_KEY:
        raise RuntimeError(
            "API_FOOTBALL_KEY manquante. Définis-la dans le fichier .env à la racine du projet."
        )
    return API_FOOTBALL_KEY


def require_gemini_key() -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY manquante. Définis-la dans le fichier .env pour utiliser la génération de rapports LLM."
        )
    return GEMINI_API_KEY
