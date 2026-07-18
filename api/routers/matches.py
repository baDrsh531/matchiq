from fastapi import APIRouter, HTTPException

from ml.ingestion import ApiFootballError, RateLimitError, fetch_fixture

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/{fixture_id}")
def get_match(fixture_id: int):
    """Infos générales du match : équipes, score, statut."""
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

    fixture_info = raw.get("fixture", {})
    teams = fixture_info.get("teams", {})
    goals = fixture_info.get("goals", {})
    status = fixture_info.get("fixture", {}).get("status", {})

    return {
        "fixture_id": fixture_id,
        "teams": teams,
        "goals": goals,
        "status": status,
        "date": fixture_info.get("fixture", {}).get("date"),
        "venue": fixture_info.get("fixture", {}).get("venue"),
        "league": fixture_info.get("league"),
        "events": raw.get("events", []),
    }
