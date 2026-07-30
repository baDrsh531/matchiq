"""Fiches "carrière" joueur/équipe — agrégées depuis l'historique en base
(persistence/), donc sans coût de quota API-Football supplémentaire :
elles ne couvrent que les matchs déjà analysés via /matches/{id}/players.
"""
from fastapi import APIRouter, HTTPException

from ml.anomalies import detect_anomalies
from ml.insights import form_summary
from ml.similarity import similar_players
from persistence.database import SessionLocal
from persistence.repository import get_player_history, get_team_history, player_profiles

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
    history["form"] = form_summary(history["matches"])
    history["anomalies"] = detect_anomalies(history["matches"])
    return history


@router.get("/players/{player_id}/similar")
def get_similar_players(player_id: int, limit: int = 5):
    """Joueurs au profil statistique le plus proche (même poste), par similarité
    cosinus sur les contributions standardisées. Agrégé depuis la base, sans coût
    de quota API-Football."""
    session = SessionLocal()
    try:
        history = get_player_history(session, player_id)
        if history is None:
            raise HTTPException(
                status_code=404,
                detail=f"Aucun historique pour le joueur {player_id}.",
            )
        pool = player_profiles(session, history["position"])
    finally:
        session.close()

    results = similar_players(player_id, pool, limit=limit)
    return {
        "player_id": player_id,
        "name": history["name"],
        "position": history["position"],
        "pool_size": len(pool),
        "similar": results,
    }


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
