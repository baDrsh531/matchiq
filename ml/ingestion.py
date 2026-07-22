"""Ingestion des données de match depuis l'API-Football (api-sports.io).

Combine 4 endpoints (fixtures, statistics, players, events) pour un fixture_id
donné, avec mise en cache locale sur disque pour économiser le quota gratuit
(100 requêtes/jour).
"""
import json
import logging
from pathlib import Path
from typing import Any

import requests

from config import API_FOOTBALL_BASE_URL, DATA_RAW_DIR, DEMO_MODE, require_api_football_key

logger = logging.getLogger("matchiq.ingestion")
logging.basicConfig(level=logging.INFO)

TIMEOUT_SECONDS = 15


class ApiFootballError(Exception):
    """Erreur renvoyée par l'API-Football (quota, fixture inconnu, etc.)."""


class RateLimitError(ApiFootballError):
    """Quota de requêtes journalier dépassé (HTTP 429)."""


class DemoModeError(ApiFootballError):
    """Appel sortant tenté alors que l'instance tourne en mode démo.

    Hérite d'ApiFootballError pour que les routers la traduisent déjà en 503
    sans modification : une donnée absente du cache est indisponible, ce qui
    est exactement la sémantique attendue côté client.
    """


def _headers() -> dict[str, str]:
    return {"x-apisports-key": require_api_football_key()}


def _get(endpoint: str, params: dict[str, Any]) -> dict:
    """Appelle un endpoint de l'API-Football et gère erreurs + quota.

    Point de passage unique vers l'extérieur : c'est ici, et nulle part
    ailleurs, que le mode démo coupe le réseau. Les fonctions appelantes
    lisent leur cache disque AVANT d'arriver ici, donc tout ce qui est déjà
    téléchargé reste servi normalement.
    """
    if DEMO_MODE:
        raise DemoModeError(
            f"Mode démo : donnée absente du cache local ({endpoint}). "
            "Cette instance publique ne sert que les matchs déjà analysés."
        )

    url = f"{API_FOOTBALL_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ApiFootballError(f"Échec réseau vers {endpoint}: {exc}") from exc

    remaining = resp.headers.get("x-ratelimit-requests-remaining")
    limit = resp.headers.get("x-ratelimit-requests-limit")
    if remaining is not None:
        logger.info("Quota API-Football restant: %s/%s (endpoint=%s)", remaining, limit, endpoint)

    if resp.status_code == 429:
        raise RateLimitError(
            f"Quota API-Football dépassé (429) sur {endpoint}. Requêtes restantes: {remaining}."
        )
    if resp.status_code != 200:
        raise ApiFootballError(f"Erreur HTTP {resp.status_code} sur {endpoint}: {resp.text[:300]}")

    payload = resp.json()
    errors = payload.get("errors")
    if errors:
        # l'API renvoie parfois {} ou [] quand tout va bien, donc on ne
        # déclenche que si errors contient réellement un message
        if isinstance(errors, dict) and errors or isinstance(errors, list) and errors:
            raise ApiFootballError(f"Erreur API-Football sur {endpoint}: {errors}")

    return payload


def fetch_fixture_info(fixture_id: int) -> dict:
    payload = _get("fixtures", {"id": fixture_id})
    response = payload.get("response") or []
    if not response:
        raise ApiFootballError(f"Fixture {fixture_id} introuvable.")
    return response[0]


def fetch_fixture_statistics(fixture_id: int) -> list[dict]:
    payload = _get("fixtures/statistics", {"fixture": fixture_id})
    return payload.get("response") or []


def fetch_fixture_players(fixture_id: int) -> list[dict]:
    payload = _get("fixtures/players", {"fixture": fixture_id})
    return payload.get("response") or []


def fetch_fixture_events(fixture_id: int) -> list[dict]:
    payload = _get("fixtures/events", {"fixture": fixture_id})
    return payload.get("response") or []


def fetch_fixture_lineups(fixture_id: int) -> list[dict]:
    payload = _get("fixtures/lineups", {"fixture": fixture_id})
    return payload.get("response") or []


def _cache_path(fixture_id: int) -> Path:
    return DATA_RAW_DIR / f"{fixture_id}.json"


_REQUIRED_KEYS = ("fixture", "statistics", "players", "events", "lineups")


def fetch_fixture(fixture_id: int, force_refresh: bool = False) -> dict:
    """Récupère et combine les 5 endpoints pour un match, avec cache disque.

    Si data/raw/{fixture_id}.json existe déjà et contient les 5 clés, on le
    réutilise directement (sauf force_refresh=True) pour ne pas gaspiller le
    quota journalier.

    Le cache est écrit de façon incrémentale après CHAQUE appel réussi : si un
    des appels échoue (ex: quota dépassé en cours de route), les appels déjà
    réussis restent en cache et ne sont pas refaits inutilement la prochaine
    fois (même après réinitialisation du quota le lendemain). Cela permet
    aussi de "compléter" silencieusement un cache existant créé avant l'ajout
    d'une nouvelle clé (ex: "lineups") : un seul appel supplémentaire au lieu
    de tout refaire.
    """
    cache_file = _cache_path(fixture_id)
    combined: dict = {"fixture_id": fixture_id}

    if cache_file.exists() and not force_refresh:
        combined = json.loads(cache_file.read_text(encoding="utf-8"))
        if all(key in combined for key in _REQUIRED_KEYS):
            logger.info("Cache trouvé pour le fixture %s, pas d'appel API.", fixture_id)
            return combined

    def _ensure(key: str, fetch_fn) -> None:
        if key in combined:
            return
        combined[key] = fetch_fn(fixture_id)
        cache_file.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    _ensure("fixture", fetch_fixture_info)
    _ensure("statistics", fetch_fixture_statistics)
    _ensure("players", fetch_fixture_players)
    _ensure("events", fetch_fixture_events)
    _ensure("lineups", fetch_fixture_lineups)

    logger.info("Fixture %s mis en cache dans %s", fixture_id, cache_file)
    return combined


def build_match_summary(fixture_id: int, raw: dict) -> dict:
    """Transforme la réponse combinée de fetch_fixture en résumé exploitable
    par l'API (équipes, score, statut, logos) et par la persistance."""
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
        "lineups": raw.get("lineups", []),
    }


def search_league(name: str) -> list[dict]:
    """Utilitaire pour vérifier la couverture d'une ligue (ex: Botola Pro)."""
    payload = _get("leagues", {"search": name})
    return payload.get("response") or []


def _standings_cache_path(league_id: int, season: int) -> Path:
    return DATA_RAW_DIR / f"standings_{league_id}_{season}.json"


def fetch_standings(league_id: int, season: int, force_refresh: bool = False) -> list[dict]:
    """Classement d'une ligue, avec cache disque (le classement ne change pas
    entre deux consultations rapprochées, inutile de réinterroger l'API)."""
    cache_file = _standings_cache_path(league_id, season)
    if cache_file.exists() and not force_refresh:
        logger.info("Cache trouvé pour le classement %s/%s, pas d'appel API.", league_id, season)
        return json.loads(cache_file.read_text(encoding="utf-8"))

    payload = _get("standings", {"league": league_id, "season": season})
    response = payload.get("response") or []
    if not response:
        raise ApiFootballError(f"Classement introuvable pour la ligue {league_id}, saison {season}.")

    standings_groups = response[0].get("league", {}).get("standings") or []
    flattened = [row for group in standings_groups for row in group]

    cache_file.write_text(json.dumps(flattened, ensure_ascii=False, indent=2), encoding="utf-8")
    return flattened


def search_teams(query: str) -> list[dict]:
    """Recherche libre d'équipe par nom (pas de cache : la liste des équipes
    évolue peu mais la recherche doit rester réactive à la frappe)."""
    payload = _get("teams", {"search": query})
    return payload.get("response") or []


def _team_fixtures_cache_path(team_id: int, season: int) -> Path:
    return DATA_RAW_DIR / f"team_fixtures_{team_id}_{season}.json"


def fetch_team_fixtures(team_id: int, season: int, force_refresh: bool = False) -> list[dict]:
    """Liste des matchs d'une équipe pour une saison, avec cache disque."""
    cache_file = _team_fixtures_cache_path(team_id, season)
    if cache_file.exists() and not force_refresh:
        logger.info(
            "Cache trouvé pour les matchs de l'équipe %s/%s, pas d'appel API.", team_id, season
        )
        return json.loads(cache_file.read_text(encoding="utf-8"))

    payload = _get("fixtures", {"team": team_id, "season": season})
    response = payload.get("response") or []

    cache_file.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
    return response
