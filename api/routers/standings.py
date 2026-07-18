from fastapi import APIRouter, HTTPException

from ml.ingestion import ApiFootballError, RateLimitError, fetch_standings

router = APIRouter(prefix="/standings", tags=["standings"])

# Ligues volontairement limitées à celles dont la couverture stats a été
# vérifiée sur le plan gratuit (voir mémoire de session) — garde le quota
# journalier (100 requêtes) sous contrôle plutôt que d'exposer une recherche
# libre qui pourrait le vider en quelques clics.
SUPPORTED_LEAGUES = [
    {"league_id": 39, "name": "Premier League", "country": "England"},
    {"league_id": 140, "name": "La Liga", "country": "Spain"},
    {"league_id": 61, "name": "Ligue 1", "country": "France"},
    {"league_id": 2, "name": "Champions League", "country": "World"},
]


@router.get("/leagues")
def get_supported_leagues():
    return {"leagues": SUPPORTED_LEAGUES}


@router.get("")
def get_standings(league_id: int = 39, season: int = 2023):
    try:
        rows = fetch_standings(league_id, season)
    except RateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiFootballError as exc:
        if "introuvable" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc

    return {"league_id": league_id, "season": season, "standings": rows}
