"""Chargement centralisé de la configuration depuis .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
API_FOOTBALL_BASE_URL = os.getenv("API_FOOTBALL_BASE_URL", "https://v3.football.api-sports.io")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/matchiq.db")

DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
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
