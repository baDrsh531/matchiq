from fastapi import APIRouter, HTTPException

from llm.report_generator import get_player_analysis
from ml.ingestion import ApiFootballError, RateLimitError
from ml.scoring_engine import rank_players

router = APIRouter(prefix="/matches", tags=["players"])


def _handle_fixture_errors(exc: Exception):
    if isinstance(exc, RateLimitError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ApiFootballError):
        if "introuvable" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise exc


@router.get("/{fixture_id}/players")
def get_players(fixture_id: int):
    """Scores composites de tous les joueurs du match, triés (MOTM en premier)."""
    try:
        return {"fixture_id": fixture_id, "players": rank_players(fixture_id)}
    except (ApiFootballError, RateLimitError) as exc:
        _handle_fixture_errors(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc


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
