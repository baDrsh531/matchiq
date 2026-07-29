import logging

from fastapi import APIRouter, HTTPException

from llm.report_generator import answer_match_question, generate_match_report
from ml.ingestion import ApiFootballError, RateLimitError
from persistence.database import SessionLocal
from persistence.repository import save_report

logger = logging.getLogger("matchiq.api")

router = APIRouter(prefix="/matches", tags=["reports"])


def _lang(value: str) -> str:
    return value if value in ("fr", "en") else "fr"


@router.get("/{fixture_id}/report")
def get_report(fixture_id: int, refresh: bool = False, lang: str = "fr"):
    """Rapport complet généré par le LLM (MOTM, analyses joueurs, tactique).

    Le rapport est mis en cache par langue après la première génération. Passer
    ?lang=en pour l'anglais, ?refresh=true pour forcer une régénération.
    """
    try:
        report = generate_match_report(fixture_id, force_refresh=refresh, lang=_lang(lang))
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

    try:
        session = SessionLocal()
        try:
            save_report(session, fixture_id, report, report.get("motm_player_id"))
        finally:
            session.close()
    except Exception:
        logger.exception("Échec de la persistance du rapport pour le fixture %s", fixture_id)

    return report


@router.get("/{fixture_id}/ask")
def ask_match(fixture_id: int, q: str, refresh: bool = False, lang: str = "fr"):
    """Question en langage naturel sur un match : la réponse est fondée
    uniquement sur les scores/stats déjà calculés (LLM ancré, anti-hallucination).

    La réponse est mise en cache par question et par langue ; reposer la même
    n'appelle pas à nouveau le LLM.
    """
    question = (q or "").strip()
    if len(question) < 3:
        raise HTTPException(status_code=400, detail="La question doit faire au moins 3 caractères.")

    try:
        return answer_match_question(fixture_id, question, force_refresh=refresh, lang=_lang(lang))
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
