"""Comparateur de matchs : deux rencontres déjà analysées côte à côte, avec les
joueurs communs. Agrégé depuis la base, sans coût de quota API-Football."""
from fastapi import APIRouter, HTTPException

from persistence.database import SessionLocal
from persistence.repository import compare_matches

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/matches")
def get_match_comparison(a: int, b: int):
    """Compare deux matchs analysés (fixture_id `a` et `b`) : scores, homme du
    match, top joueurs, et joueurs communs avec l'écart de note entre les deux."""
    session = SessionLocal()
    try:
        result = compare_matches(session, a, b)
    finally:
        session.close()

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Un des deux matchs n'a pas été analysé. Analyse-les d'abord via /matches/{id}/players.",
        )
    return result
