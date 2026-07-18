import logging

from fastapi import APIRouter, HTTPException

from llm.report_generator import get_player_analysis
from ml.ingestion import ApiFootballError, RateLimitError, build_match_summary, fetch_fixture
from ml.scoring_engine import rank_players
from persistence.database import SessionLocal
from persistence.repository import save_match_snapshot

logger = logging.getLogger("matchiq.api")

router = APIRouter(prefix="/matches", tags=["players"])


def _handle_fixture_errors(exc: Exception):
    if isinstance(exc, RateLimitError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ApiFootballError):
        if "introuvable" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise exc


def _persist_snapshot(fixture_id: int, players: list[dict]) -> None:
    """Sauvegarde l'instantané en base pour l'historique. Ne doit jamais faire
    échouer la requête principale si l'écriture DB pose problème."""
    try:
        raw = fetch_fixture(fixture_id)
        match_info = build_match_summary(fixture_id, raw)
        session = SessionLocal()
        try:
            save_match_snapshot(session, match_info, players)
        finally:
            session.close()
    except Exception:
        logger.exception("Échec de la persistance de l'instantané pour le fixture %s", fixture_id)


@router.get("/{fixture_id}/players")
def get_players(fixture_id: int):
    """Scores composites de tous les joueurs du match, triés (MOTM en premier)."""
    try:
        players = rank_players(fixture_id)
    except (ApiFootballError, RateLimitError) as exc:
        _handle_fixture_errors(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc

    _persist_snapshot(fixture_id, players)
    return {"fixture_id": fixture_id, "players": players}


@router.get("/{fixture_id}/player/{player_id}")
def get_player_detail(fixture_id: int, player_id: int):
    """Détail d'un joueur : score composite, radar chart, analyse LLM."""
    try:
        return get_player_analysis(fixture_id, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ApiFootballError, RateLimitError) as exc:
        _handle_fixture_errors(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc
