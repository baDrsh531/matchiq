"""Tests d'intégration des routes HTTP.

Deux isolations sont nécessaires pour que ces tests ne touchent ni le réseau
ni la base réelle :

1. la base — les routers appellent `SessionLocal()` importé dans leur propre
   module, donc on remplace ce symbole module par module (fixture `api_db`) ;
2. l'API-Football et le LLM — on remplace les fonctions d'ingestion et de
   génération là où elles sont utilisées, pas à leur définition.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api import main
from api.routers import matches, players, profiles, reports, search, standings
from ml.ingestion import ApiFootballError, RateLimitError
from persistence.database import Base
from persistence.repository import save_match_snapshot

# Les modules qui ouvrent eux-mêmes une session
_ROUTERS_WITH_DB = (matches, players, profiles, reports, search)


@pytest.fixture
def api_db(monkeypatch):
    """Base SQLite en mémoire, partagée par tous les routers le temps du test.

    `StaticPool` est indispensable : sans lui, chaque nouvelle connexion à
    `sqlite:///:memory:` ouvre une base vierge, et les sessions ouvertes par les
    routers ne verraient aucune des tables créées ici.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    for module in _ROUTERS_WITH_DB:
        monkeypatch.setattr(module, "SessionLocal", TestSession, raising=False)
    # évite que le startup de l'app ne recrée les tables sur la vraie base
    monkeypatch.setattr(main, "init_db", lambda: None)

    return TestSession


@pytest.fixture
def client(api_db):
    with TestClient(main.app) as c:
        yield c


# --------------------------------------------------------------------------
# Jeux de données
# --------------------------------------------------------------------------

def _match_info(fixture_id=1035038):
    return {
        "fixture_id": fixture_id,
        "teams": {
            "home": {"id": 42, "name": "Arsenal", "logo": "logo42.png"},
            "away": {"id": 65, "name": "Nottingham Forest", "logo": "logo65.png"},
        },
        "goals": {"home": 2, "away": 1},
        "date": "2023-08-12T11:30:00+00:00",
        "venue": {"name": "Emirates Stadium"},
        "league": {"name": "Premier League", "logo": "logo39.png"},
    }


def _player(player_id=1, name="Thomas Partey", score=10.0):
    return {
        "player_id": player_id,
        "name": name,
        "photo_url": f"player{player_id}.png",
        "team_id": 42,
        "team_name": "Arsenal",
        "team_logo": "logo42.png",
        "position": "Midfielder",
        "minutes": 90,
        "composite_score": score,
        "breakdown": {"tackles": 0.3},
        "radar": {"tacles": 9.0},
        "strengths": ["tacles"],
        "weaknesses": [],
    }


# --------------------------------------------------------------------------
# /health
# --------------------------------------------------------------------------

def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    # exposé pour qu'un client sache si l'instance est en lecture seule
    assert body["demo_mode"] is False


# --------------------------------------------------------------------------
# /matches
# --------------------------------------------------------------------------

def test_get_recent_matches_empty_by_default(client):
    r = client.get("/matches")
    assert r.status_code == 200
    assert r.json() == {"matches": []}


def test_get_recent_matches_lists_persisted_matches(client, api_db):
    session = api_db()
    save_match_snapshot(session, _match_info(), [_player()])
    session.close()

    r = client.get("/matches")
    assert r.status_code == 200
    body = r.json()["matches"]
    assert len(body) == 1
    assert body[0]["fixture_id"] == 1035038
    assert body[0]["home_team"]["name"] == "Arsenal"


def test_get_match_returns_summary(client, monkeypatch):
    monkeypatch.setattr(matches, "fetch_fixture", lambda fid: {"raw": fid})
    monkeypatch.setattr(matches, "build_match_summary", lambda fid, raw: _match_info(fid))

    r = client.get("/matches/1035038")
    assert r.status_code == 200
    assert r.json()["goals"] == {"home": 2, "away": 1}


def test_get_match_unknown_fixture_returns_404(client, monkeypatch):
    def boom(_):
        raise ApiFootballError("Fixture introuvable")

    monkeypatch.setattr(matches, "fetch_fixture", boom)
    r = client.get("/matches/999")
    assert r.status_code == 404


def test_get_match_rate_limited_returns_503(client, monkeypatch):
    def boom(_):
        raise RateLimitError("Quota journalier atteint")

    monkeypatch.setattr(matches, "fetch_fixture", boom)
    r = client.get("/matches/1035038")
    assert r.status_code == 503


def test_get_match_unexpected_error_returns_500(client, monkeypatch):
    def boom(_):
        raise TypeError("bug interne")

    monkeypatch.setattr(matches, "fetch_fixture", boom)
    r = client.get("/matches/1035038")
    assert r.status_code == 500


# --------------------------------------------------------------------------
# /matches/{id}/players et /player/{id}
# --------------------------------------------------------------------------

def test_get_players_returns_ranked_list(client, monkeypatch):
    monkeypatch.setattr(players, "rank_players", lambda fid: [_player(), _player(2, "Saka", 8.5)])
    monkeypatch.setattr(players, "fetch_fixture", lambda fid: {})
    monkeypatch.setattr(players, "build_match_summary", lambda fid, raw: _match_info(fid))

    r = client.get("/matches/1035038/players")
    assert r.status_code == 200
    body = r.json()
    assert body["fixture_id"] == 1035038
    assert [p["name"] for p in body["players"]] == ["Thomas Partey", "Saka"]


def test_get_players_persists_snapshot_for_history(client, monkeypatch):
    monkeypatch.setattr(players, "rank_players", lambda fid: [_player()])
    monkeypatch.setattr(players, "fetch_fixture", lambda fid: {})
    monkeypatch.setattr(players, "build_match_summary", lambda fid, raw: _match_info(fid))

    client.get("/matches/1035038/players")

    # le match doit désormais apparaître dans l'historique
    assert client.get("/matches").json()["matches"][0]["fixture_id"] == 1035038


def test_get_players_survives_persistence_failure(client, monkeypatch):
    """Une panne d'écriture en base ne doit pas faire échouer la requête."""
    monkeypatch.setattr(players, "rank_players", lambda fid: [_player()])

    def boom(_):
        raise RuntimeError("base indisponible")

    monkeypatch.setattr(players, "fetch_fixture", boom)

    r = client.get("/matches/1035038/players")
    assert r.status_code == 200
    assert len(r.json()["players"]) == 1


def test_get_players_rate_limited_returns_503(client, monkeypatch):
    def boom(_):
        raise RateLimitError("Quota atteint")

    monkeypatch.setattr(players, "rank_players", boom)
    assert client.get("/matches/1035038/players").status_code == 503


def test_get_player_detail_returns_analysis(client, monkeypatch):
    monkeypatch.setattr(
        players, "get_player_analysis",
        lambda fid, pid: {"player_id": pid, "analysis": "Match solide.", "radar": {"tacles": 9.0}},
    )
    r = client.get("/matches/1035038/player/1")
    assert r.status_code == 200
    assert r.json()["analysis"] == "Match solide."


def test_get_player_detail_unknown_player_returns_404(client, monkeypatch):
    def boom(fid, pid):
        raise ValueError("Joueur absent de la feuille de match")

    monkeypatch.setattr(players, "get_player_analysis", boom)
    assert client.get("/matches/1035038/player/999").status_code == 404


def test_get_player_detail_missing_llm_key_returns_503(client, monkeypatch):
    def boom(fid, pid):
        raise RuntimeError("GEMINI_API_KEY manquante")

    monkeypatch.setattr(players, "get_player_analysis", boom)
    assert client.get("/matches/1035038/player/1").status_code == 503


# --------------------------------------------------------------------------
# /matches/{id}/report
# --------------------------------------------------------------------------

def _report():
    return {
        "motm_report": "Partey a tenu l'entrejeu.",
        "player_reports": {"1": "Solide."},
        "tactical_suggestions": {"Arsenal": "Presser plus haut."},
        "motm_player_id": 1,
    }


def test_get_report_returns_generated_report(client, monkeypatch):
    monkeypatch.setattr(reports, "generate_match_report", lambda fid, force_refresh=False: _report())
    r = client.get("/matches/1035038/report")
    assert r.status_code == 200
    assert r.json()["motm_report"].startswith("Partey")


def test_get_report_passes_refresh_flag(client, monkeypatch):
    seen = {}

    def fake(fid, force_refresh=False):
        seen["refresh"] = force_refresh
        return _report()

    monkeypatch.setattr(reports, "generate_match_report", fake)
    client.get("/matches/1035038/report?refresh=true")
    assert seen["refresh"] is True


def test_get_report_persists_and_flags_match(client, api_db, monkeypatch):
    session = api_db()
    save_match_snapshot(session, _match_info(), [_player()])
    session.close()

    monkeypatch.setattr(reports, "generate_match_report", lambda fid, force_refresh=False: _report())
    client.get("/matches/1035038/report")

    assert client.get("/matches").json()["matches"][0]["has_report"] is True


def test_get_report_missing_llm_key_returns_503(client, monkeypatch):
    def boom(fid, force_refresh=False):
        raise RuntimeError("GEMINI_API_KEY manquante")

    monkeypatch.setattr(reports, "generate_match_report", boom)
    assert client.get("/matches/1035038/report").status_code == 503


# --------------------------------------------------------------------------
# /players/{id}/history et /teams/{id}/history
# --------------------------------------------------------------------------

def test_player_history_returns_404_when_never_analysed(client):
    assert client.get("/players/999/history").status_code == 404


def test_player_history_aggregates_after_analysis(client, api_db):
    session = api_db()
    save_match_snapshot(session, _match_info(), [_player()])
    session.close()

    r = client.get("/players/1/history")
    assert r.status_code == 200
    assert r.json()["matches_played"] == 1


def test_team_history_returns_404_when_unknown(client):
    assert client.get("/teams/424242/history").status_code == 404


def test_team_history_returns_squad(client, api_db):
    session = api_db()
    save_match_snapshot(session, _match_info(), [_player()])
    session.close()

    r = client.get("/teams/42/history")
    assert r.status_code == 200
    assert r.json()["team_name"] == "Arsenal"


# --------------------------------------------------------------------------
# /standings
# --------------------------------------------------------------------------

def test_supported_leagues_listed(client):
    r = client.get("/standings/leagues")
    assert r.status_code == 200
    ids = [lg["league_id"] for lg in r.json()["leagues"]]
    assert 39 in ids and 140 in ids


def test_standings_returns_rows(client, monkeypatch):
    monkeypatch.setattr(standings, "fetch_standings", lambda lid, s: [{"rank": 1, "team": "Arsenal"}])
    r = client.get("/standings?league_id=39&season=2023")
    body = r.json()
    assert r.status_code == 200
    assert body["league_id"] == 39 and body["season"] == 2023
    assert body["standings"][0]["rank"] == 1


def test_standings_unknown_league_returns_404(client, monkeypatch):
    def boom(lid, s):
        raise ApiFootballError("Classement introuvable")

    monkeypatch.setattr(standings, "fetch_standings", boom)
    assert client.get("/standings?league_id=999").status_code == 404


def test_standings_rate_limited_returns_503(client, monkeypatch):
    def boom(lid, s):
        raise RateLimitError("Quota atteint")

    monkeypatch.setattr(standings, "fetch_standings", boom)
    assert client.get("/standings").status_code == 503


# --------------------------------------------------------------------------
# /search
# --------------------------------------------------------------------------

def test_search_teams_rejects_short_query(client):
    r = client.get("/search/teams?query=ar")
    assert r.status_code == 400


def test_search_teams_maps_api_payload(client, monkeypatch):
    monkeypatch.setattr(
        search, "search_teams",
        lambda q: [{"team": {"id": 42, "name": "Arsenal", "logo": "l.png", "country": "England"}}],
    )
    r = client.get("/search/teams?query=arsenal")
    assert r.status_code == 200
    team = r.json()["teams"][0]
    assert team["id"] == 42
    assert team["national"] is False  # valeur par défaut quand absente


def test_search_teams_rate_limited_returns_503(client, monkeypatch):
    def boom(q):
        raise RateLimitError("Quota atteint")

    monkeypatch.setattr(search, "search_teams", boom)
    assert client.get("/search/teams?query=arsenal").status_code == 503


def test_team_fixtures_maps_api_payload(client, monkeypatch):
    monkeypatch.setattr(
        search, "fetch_team_fixtures",
        lambda tid, season: [
            {
                "fixture": {"id": 1035038, "date": "2023-08-12T11:30:00+00:00",
                            "status": {"short": "FT"}},
                "teams": {"home": {"name": "Arsenal"}, "away": {"name": "Forest"}},
                "goals": {"home": 2, "away": 1},
                "league": {"name": "Premier League"},
            }
        ],
    )
    r = client.get("/search/teams/42/fixtures?season=2023")
    assert r.status_code == 200
    assert r.json()["fixtures"][0]["fixture_id"] == 1035038


def test_search_players_rejects_short_query(client):
    assert client.get("/search/players?query=a").status_code == 400


def test_search_players_finds_persisted_player(client, api_db):
    session = api_db()
    save_match_snapshot(session, _match_info(), [_player(name="Thomas Partey")])
    session.close()

    r = client.get("/search/players?query=partey")
    assert r.status_code == 200
    assert r.json()["players"][0]["name"] == "Thomas Partey"
