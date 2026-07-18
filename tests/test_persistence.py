import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from persistence.database import Base
from persistence.repository import (
    get_player_history,
    get_team_history,
    list_matches,
    save_match_snapshot,
    save_report,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()
    yield db
    db.close()


def _match_info(fixture_id=1035038):
    return {
        "fixture_id": fixture_id,
        "teams": {
            "home": {"id": 42, "name": "Arsenal", "logo": "https://media.api-sports.io/football/teams/42.png"},
            "away": {"id": 65, "name": "Nottingham Forest", "logo": "https://media.api-sports.io/football/teams/65.png"},
        },
        "goals": {"home": 2, "away": 1},
        "date": "2023-08-12T11:30:00+00:00",
        "venue": {"name": "Emirates Stadium"},
        "league": {"name": "Premier League", "logo": "https://media.api-sports.io/football/leagues/39.png"},
    }


def _player(player_id, team_name="Arsenal", team_id=42, score=8.0):
    return {
        "player_id": player_id,
        "name": f"Player {player_id}",
        "photo_url": f"https://media.api-sports.io/football/players/{player_id}.png",
        "team_id": team_id,
        "team_name": team_name,
        "team_logo": "https://media.api-sports.io/football/teams/42.png",
        "position": "Midfielder",
        "minutes": 90,
        "composite_score": score,
        "breakdown": {"passes_accuracy": 0.1},
        "radar": {"précision des passes": 8.0},
        "strengths": ["précision des passes"],
        "weaknesses": [],
    }


def test_save_match_snapshot_creates_match_and_players(session):
    players = [_player(1, score=9.0), _player(2, score=5.0)]
    save_match_snapshot(session, _match_info(), players)

    matches = list_matches(session)
    assert len(matches) == 1
    m = matches[0]
    assert m["fixture_id"] == 1035038
    assert m["home_team"]["name"] == "Arsenal"
    assert m["home_team"]["logo"].endswith("42.png")
    assert m["goals"] == {"home": 2, "away": 1}
    assert m["has_report"] is False


def test_save_match_snapshot_upserts_on_second_call(session):
    save_match_snapshot(session, _match_info(), [_player(1, score=9.0)])
    save_match_snapshot(session, _match_info(), [_player(1, score=7.0), _player(2, score=3.0)])

    matches = list_matches(session)
    assert len(matches) == 1  # pas de doublon


def test_save_report_marks_has_report_true(session):
    save_match_snapshot(session, _match_info(), [_player(1)])
    save_report(
        session,
        1035038,
        {
            "motm_report": "Excellent match.",
            "player_reports": {"1": "Bon match."},
            "tactical_suggestions": {"Arsenal": "Presser plus haut."},
        },
        motm_player_id=1,
    )

    matches = list_matches(session)
    assert matches[0]["has_report"] is True


def test_list_matches_orders_most_recent_first(session):
    save_match_snapshot(session, _match_info(fixture_id=1), [_player(1)])
    time.sleep(0.01)  # garantit un `analyzed_at` distinct entre les deux inserts
    save_match_snapshot(session, _match_info(fixture_id=2), [_player(1)])

    matches = list_matches(session)
    assert [m["fixture_id"] for m in matches] == [2, 1]


def _match_info_2(fixture_id=2000000):
    return {
        "fixture_id": fixture_id,
        "teams": {
            "home": {"id": 42, "name": "Arsenal", "logo": "https://media.api-sports.io/football/teams/42.png"},
            "away": {"id": 99, "name": "Chelsea", "logo": "https://media.api-sports.io/football/teams/99.png"},
        },
        "goals": {"home": 1, "away": 1},
        "date": "2023-09-01T15:00:00+00:00",
        "venue": {"name": "Emirates Stadium"},
        "league": {"name": "Premier League", "logo": "https://media.api-sports.io/football/leagues/39.png"},
    }


def test_get_player_history_returns_none_when_never_played(session):
    assert get_player_history(session, 999) is None


def test_get_player_history_aggregates_across_matches(session):
    save_match_snapshot(session, _match_info(), [_player(1, score=9.0)])
    save_match_snapshot(session, _match_info_2(), [_player(1, score=5.0)])

    history = get_player_history(session, 1)
    assert history["matches_played"] == 2
    assert history["average_score"] == 7.0
    assert history["team_id"] == 42
    assert history["radar"] == {"précision des passes": 8.0}
    assert [m["fixture_id"] for m in history["matches"]] == [1035038, 2000000]
    assert history["matches"][0]["opponent_name"] == "Nottingham Forest"
    assert history["matches"][1]["opponent_name"] == "Chelsea"


def test_get_team_history_returns_none_when_unknown(session):
    assert get_team_history(session, 424242) is None


def test_get_team_history_builds_squad_from_appearances(session):
    save_match_snapshot(
        session, _match_info(), [_player(1, score=9.0), _player(2, score=5.0)]
    )
    save_match_snapshot(session, _match_info_2(), [_player(1, score=5.0)])

    history = get_team_history(session, 42)
    assert history["team_name"] == "Arsenal"
    assert len(history["matches"]) == 2
    squad_by_id = {p["player_id"]: p for p in history["squad"]}
    assert squad_by_id[1]["appearances"] == 2
    assert squad_by_id[1]["average_score"] == 7.0
    assert squad_by_id[2]["appearances"] == 1
