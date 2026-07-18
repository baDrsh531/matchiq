"""Modèles Pydantic pour les stats brutes et les scores calculés."""
from typing import Optional

from pydantic import BaseModel, Field

POSITION_CODE_MAP = {
    "G": "Goalkeeper",
    "D": "Defender",
    "M": "Midfielder",
    "F": "Attacker",
}


class PlayerMatchStats(BaseModel):
    """Stats brutes d'un joueur pour un match, extraites de fixtures/players."""

    player_id: int
    name: str
    photo_url: Optional[str] = None
    team_id: int
    team_name: str
    team_logo: Optional[str] = None
    position: str  # nom complet normalisé : Goalkeeper / Defender / Midfielder / Attacker
    minutes: int = 0
    rating: Optional[float] = None
    captain: bool = False
    substitute: bool = False

    shots_total: int = 0
    shots_on_target: int = 0

    goals: int = 0
    goals_conceded: int = 0
    assists: int = 0
    saves: int = 0

    passes_total: int = 0
    passes_key: int = 0
    passes_accuracy: float = 0.0  # pourcentage 0-100

    tackles: int = 0
    blocks: int = 0
    interceptions: int = 0

    duels_total: int = 0
    duels_won: int = 0

    dribbles_attempts: int = 0
    dribbles_success: int = 0

    fouls_drawn: int = 0
    fouls_committed: int = 0

    cards_yellow: int = 0
    cards_red: int = 0

    penalty_scored: int = 0
    penalty_missed: int = 0
    penalty_saved: int = 0


class PlayerScore(BaseModel):
    """Résultat du moteur de scoring pour un joueur."""

    player_id: int
    name: str
    photo_url: Optional[str] = None
    team_id: int
    team_name: str
    team_logo: Optional[str] = None
    position: str
    minutes: int
    composite_score: float = Field(..., ge=0, le=10)
    breakdown: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]


class FixtureData(BaseModel):
    """Payload combiné retourné par l'ingestion (fixture + stats + events)."""

    fixture_id: int
    raw: dict
