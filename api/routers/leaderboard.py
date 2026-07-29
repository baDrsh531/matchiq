"""Palmarès : meilleures performances individuelles sur tous les matchs analysés.
Agrégé depuis la base (persistence/), sans coût de quota API-Football."""
from fastapi import APIRouter

from persistence.database import SessionLocal
from persistence.repository import available_positions, top_performances

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard")
def get_leaderboard(limit: int = 20, position: str | None = None):
    """Classement des meilleures notes composites, tous matchs confondus.
    `position` filtre par poste (Goalkeeper/Defender/Midfielder/Attacker)."""
    limit = max(1, min(limit, 100))
    session = SessionLocal()
    try:
        return {
            "performances": top_performances(session, limit=limit, position=position),
            "positions": available_positions(session),
        }
    finally:
        session.close()
