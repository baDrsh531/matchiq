"""Tableau de bord FinOps/MLOps du LLM : coût, tokens, latence, taux de succès,
agrégés depuis les métriques enregistrées à chaque appel (llm/metrics)."""
from fastapi import APIRouter

from llm.metrics import summary

router = APIRouter(prefix="/llm", tags=["llm-ops"])


@router.get("/metrics")
def get_llm_metrics(recent: int = 20):
    """Synthèse d'usage du LLM. Vide tant qu'aucun appel n'a été enregistré
    (ex. instance en mode démo, où la génération est désactivée)."""
    return summary(recent=recent)
