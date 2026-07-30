from fastapi import APIRouter, HTTPException

from context.press_bridge import PressUnavailableError, match_press
from ml.ingestion import ApiFootballError, RateLimitError, build_match_summary, fetch_fixture
from persistence.database import SessionLocal
from persistence.models import MatchRecord
from persistence.repository import list_matches

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("")
def get_recent_matches(limit: int = 50):
    """Historique des matchs déjà analysés (persisté en base), pour la page d'accueil."""
    session = SessionLocal()
    try:
        return {"matches": list_matches(session, limit=limit)}
    finally:
        session.close()


@router.get("/{fixture_id}")
def get_match(fixture_id: int):
    """Infos générales du match : équipes, score, statut, timeline des événements."""
    try:
        raw = fetch_fixture(fixture_id)
    except RateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiFootballError as exc:
        if "introuvable" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc

    return build_match_summary(fixture_id, raw)


@router.get("/{fixture_id}/press")
def get_match_press(fixture_id: int, limit: int = 5):
    """Revue de presse externe du match (contexte cité, NON vérifié, séparé des
    données calculées). Noms d'équipes lus en base : aucun coût de quota API.
    Désactivée en mode démo (appel sortant)."""
    session = SessionLocal()
    try:
        record = session.get(MatchRecord, fixture_id)
    finally:
        session.close()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Match {fixture_id} non analysé — analyse-le d'abord via /matches/{{id}}/players.",
        )
    try:
        return match_press(record.home_team_name, record.away_team_name,
                           league=record.league_name, limit=limit)
    except PressUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
