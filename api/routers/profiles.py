"""Fiches "carrière" joueur/équipe — agrégées depuis l'historique en base
(persistence/), donc sans coût de quota API-Football supplémentaire :
elles ne couvrent que les matchs déjà analysés via /matches/{id}/players.
"""
from fastapi import APIRouter, HTTPException

from persistence.database import SessionLocal
from persistence.repository import get_player_history, get_team_history

router = APIRouter(tags=["profiles"])


@router.get("/players/{player_id}/history")
def get_player_profile(player_id: int):
    session = SessionLocal()
    try:
        history = get_player_history(session, player_id)
    finally:
        session.close()

    if history is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucun historique pour le joueur {player_id}. "
                "Analyse d'abord un match où il a joué via /matches/{fixture_id}/players."
            ),
        )
    return history


@router.get("/teams/{team_id}/history")
def get_team_profile(team_id: int):
    session = SessionLocal()
    try:
        history = get_team_history(session, team_id)
    finally:
        session.close()

    if history is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Aucun historique pour l'équipe {team_id}. "
                "Analyse d'abord un match de cette équipe via /matches/{fixture_id}/players."
            ),
        )
    return history
