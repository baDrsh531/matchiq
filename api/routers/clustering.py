"""Regroupement des équipes analysées par style de jeu (k-means non supervisé).

Les features viennent des statistiques collectives déjà en cache (aucun appel
API neuf). Le clustering ne devient parlant qu'avec assez d'équipes : en-deçà,
l'endpoint le dit franchement plutôt que d'inventer des familles sur 3 équipes."""
from fastapi import APIRouter

from ml.clustering import cluster_teams, extract_team_features
from ml.ingestion import load_cached_fixture
from persistence.database import SessionLocal
from persistence.repository import list_matches

router = APIRouter(prefix="/clustering", tags=["clustering"])


@router.get("/teams")
def get_team_clusters(k: int = 3):
    """Clusters de style des équipes présentes dans les matchs analysés.

    Ne lit QUE les fixtures déjà en cache (aucun appel API, aucun coût de quota) :
    un match dont le cache complet manque est simplement ignoré."""
    session = SessionLocal()
    try:
        matches = list_matches(session, limit=200)
    finally:
        session.close()

    fixtures = [raw for m in matches
                if (raw := load_cached_fixture(m["fixture_id"])) is not None]
    teams = extract_team_features(fixtures)
    return cluster_teams(teams, k=k)
