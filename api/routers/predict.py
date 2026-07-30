"""Prédiction pré-match : probabilités V/N/D issues d'un classement Elo déterministe
construit sur les résultats d'une ligue-saison (1 appel API, puis servi du cache).

Le mode démo n'a pas accès à l'API : seules les ligues-saisons déjà en cache
répondent (les autres renvoient 503, sémantique « indisponible »)."""
from fastapi import APIRouter, HTTPException

from llm.llm_client import LLMQuotaError
from llm.report_generator import comment_prediction
from ml.ingestion import ApiFootballError, DemoModeError, RateLimitError
from ml.prediction import league_table, predict_fixture, predict_matchup

router = APIRouter(prefix="/predict", tags=["predict"])

# Ligues-saisons proposées pour la prédiction — couverture vérifiée sur le plan
# gratuit (2022-2024). Une saison = un seul appel de résultats, donc le quota
# reste maîtrisé même en exposant plusieurs ligues.
SUPPORTED = [
    {"league_id": 61, "name": "Ligue 1", "country": "France", "seasons": [2023, 2022]},
    {"league_id": 39, "name": "Premier League", "country": "England", "seasons": [2023, 2022]},
    {"league_id": 140, "name": "La Liga", "country": "Spain", "seasons": [2023, 2022]},
    {"league_id": 200, "name": "Botola Pro", "country": "Morocco", "seasons": [2023, 2022]},
]


def _guard(exc: Exception) -> HTTPException:
    if isinstance(exc, RateLimitError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ApiFootballError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}")


@router.get("/leagues")
def supported_leagues():
    return {"leagues": SUPPORTED}


@router.get("/table")
def get_table(league_id: int = 61, season: int = 2023):
    """Classement Elo trié + calibration (score de Brier walk-forward) de la ligue."""
    try:
        return league_table(league_id, season)
    except (ApiFootballError, ValueError) as exc:
        raise _guard(exc) from exc
    except Exception as exc:
        raise _guard(exc) from exc


@router.get("/matchup")
def get_matchup(home: str, away: str, league_id: int = 61, season: int = 2023):
    """Pronostic d'une affiche (home vs away, par id ou par nom)."""
    try:
        return predict_matchup(league_id, season, home, away)
    except (ApiFootballError, ValueError) as exc:
        raise _guard(exc) from exc
    except Exception as exc:
        raise _guard(exc) from exc


@router.get("/fixture/{fixture_id}")
def get_fixture_prediction(fixture_id: int, league_id: int = 61, season: int = 2023):
    """Pronostic pré-match d'un match précis (entraîné sur les matchs antérieurs)
    confronté à son résultat réel."""
    try:
        return predict_fixture(league_id, season, fixture_id)
    except (ApiFootballError, ValueError) as exc:
        raise _guard(exc) from exc
    except Exception as exc:
        raise _guard(exc) from exc


@router.get("/fixture/{fixture_id}/comment")
def get_fixture_comment(fixture_id: int, league_id: int = 61, season: int = 2023,
                        lang: str = "fr", refresh: bool = False):
    """Pronostic pré-match + commentaire LLM (prédiction vs résultat réel). En mode
    démo, seul un commentaire déjà en cache répond (503 sinon)."""
    lang = lang if lang in ("fr", "en") else "fr"
    try:
        return comment_prediction(league_id, season, fixture_id, force_refresh=refresh, lang=lang)
    except LLMQuotaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DemoModeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ApiFootballError, ValueError) as exc:
        raise _guard(exc) from exc
    except Exception as exc:
        raise _guard(exc) from exc
