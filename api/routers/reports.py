from fastapi import APIRouter, HTTPException

from llm.report_generator import generate_match_report
from ml.ingestion import ApiFootballError, RateLimitError

router = APIRouter(prefix="/matches", tags=["reports"])


@router.get("/{fixture_id}/report")
def get_report(fixture_id: int, refresh: bool = False):
    """Rapport complet généré par le LLM (MOTM, analyses joueurs, tactique).

    Le rapport est mis en cache après la première génération. Passer
    ?refresh=true pour forcer une régénération (consomme des tokens LLM).
    """
    try:
        return generate_match_report(fixture_id, force_refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ApiFootballError as exc:
        if "introuvable" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur serveur inattendue: {exc}") from exc
