from fastapi import APIRouter, HTTPException

from ml.ingestion import ApiFootballError, RateLimitError, build_match_summary, fetch_fixture
from persistence.database import SessionLocal
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
