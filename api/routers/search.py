from fastapi import APIRouter, HTTPException

from ml.ingestion import ApiFootballError, RateLimitError, fetch_team_fixtures, search_teams
from persistence.database import SessionLocal
from persistence.repository import search_players

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/teams")
def search_teams_endpoint(query: str):
    if len(query) < 3:
        raise HTTPException(status_code=400, detail="La recherche nécessite au moins 3 caractères.")

    try:
        results = search_teams(query)
    except RateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc

    return {
        "teams": [
            {
                "id": t["team"]["id"],
                "name": t["team"]["name"],
                "logo": t["team"]["logo"],
                "country": t["team"].get("country"),
                "national": t["team"].get("national", False),
            }
            for t in results
        ]
    }


@router.get("/teams/{team_id}/fixtures")
def team_fixtures_endpoint(team_id: int, season: int = 2023):
    try:
        fixtures = fetch_team_fixtures(team_id, season)
    except RateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiFootballError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc

    return {
        "fixtures": [
            {
                "fixture_id": f["fixture"]["id"],
                "date": f["fixture"]["date"],
                "status": f["fixture"]["status"]["short"],
                "home_team": f["teams"]["home"],
                "away_team": f["teams"]["away"],
                "goals": f["goals"],
                "league_name": f["league"]["name"],
            }
            for f in fixtures
        ]
    }


@router.get("/players")
def search_players_endpoint(query: str):
    if len(query) < 2:
        raise HTTPException(status_code=400, detail="La recherche nécessite au moins 2 caractères.")

    session = SessionLocal()
    try:
        results = search_players(session, query)
    finally:
        session.close()
    return {"players": results}
