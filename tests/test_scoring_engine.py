import pytest

from ml import scoring_engine
from ml.schemas import PlayerMatchStats


def make_stats(**overrides) -> PlayerMatchStats:
    base = dict(
        player_id=1,
        name="Test Player",
        team_id=10,
        team_name="Test FC",
        position="Midfielder",
        minutes=90,
    )
    base.update(overrides)
    return PlayerMatchStats(**base)


def test_compute_player_score_returns_score_in_range():
    stats = make_stats(
        position="Attacker",
        goals=2,
        shots_on_target=4,
        assists=1,
        dribbles_success=3,
        duels_won=5,
        passes_key=2,
    )
    result = scoring_engine.compute_player_score(stats, "Attacker")
    assert result["player_id"] == 1
    assert result["position"] == "Attacker"
    assert set(result["breakdown"].keys()) == set(
        scoring_engine.POSITION_WEIGHTS["Attacker"].keys()
    )
    assert isinstance(result["strengths"], list)
    assert isinstance(result["weaknesses"], list)


def test_goalkeeper_with_zero_saves_does_not_crash():
    stats = make_stats(
        position="Goalkeeper",
        saves=0,
        goals_conceded=2,
        passes_accuracy=60.0,
        duels_won=0,
    )
    result = scoring_engine.compute_player_score(stats, "Goalkeeper")
    assert result["breakdown"]["saves"] == 0.0
    # buts encaissés doit être une contribution négative
    assert result["breakdown"]["goals_conceded"] < 0


def test_substitute_entering_late_has_low_but_valid_score():
    stats = make_stats(
        position="Midfielder",
        minutes=5,
        substitute=True,
        passes_total=3,
        passes_accuracy=100.0,
    )
    result = scoring_engine.compute_player_score(stats, "Midfielder")
    assert result["minutes"] == 5
    # pas de division par zéro ni de valeur aberrante
    assert -1.0 <= result["raw_score"] <= 1.5


def test_unknown_position_falls_back_to_midfielder():
    stats = make_stats(position="Unknown")
    result = scoring_engine.compute_player_score(stats, "Unknown")
    assert result["breakdown"].keys() == scoring_engine.POSITION_WEIGHTS["Midfielder"].keys()


def _fake_raw_fixture() -> dict:
    def player_entry(player_id, name, position, minutes, **stat_overrides):
        stats = {
            "games": {"minutes": minutes, "position": position, "rating": "7.0"},
            "shots": {"total": stat_overrides.get("shots_total", 0), "on": stat_overrides.get("shots_on_target", 0)},
            "goals": {
                "total": stat_overrides.get("goals", 0),
                "conceded": stat_overrides.get("goals_conceded", 0),
                "assists": stat_overrides.get("assists", 0),
                "saves": stat_overrides.get("saves", 0),
            },
            "passes": {
                "total": stat_overrides.get("passes_total", 20),
                "key": stat_overrides.get("passes_key", 0),
                "accuracy": stat_overrides.get("passes_accuracy", 80),
            },
            "tackles": {
                "total": stat_overrides.get("tackles", 0),
                "blocks": stat_overrides.get("blocks", 0),
                "interceptions": stat_overrides.get("interceptions", 0),
            },
            "duels": {"total": 5, "won": stat_overrides.get("duels_won", 2)},
            "dribbles": {"attempts": 2, "success": stat_overrides.get("dribbles_success", 0)},
            "fouls": {"drawn": 0, "committed": stat_overrides.get("fouls_committed", 0)},
            "cards": {"yellow": stat_overrides.get("cards_yellow", 0), "red": stat_overrides.get("cards_red", 0)},
            "penalty": {"won": 0, "commited": 0, "scored": 0, "missed": 0, "saved": 0},
        }
        return {"player": {"id": player_id, "name": name}, "statistics": [stats]}

    return {
        "fixture_id": 999999,
        "players": [
            {
                "team": {"id": 1, "name": "Home FC"},
                "players": [
                    player_entry(1, "Star Striker", "F", 90, goals=2, shots_on_target=4, assists=1),
                    player_entry(2, "Solid Keeper", "G", 90, saves=5, goals_conceded=0),
                ],
            },
            {
                "team": {"id": 2, "name": "Away FC"},
                "players": [
                    player_entry(3, "Weak Striker", "F", 90, goals=0, shots_on_target=0),
                    player_entry(4, "Bench Sub", "M", 3, passes_total=1),
                ],
            },
        ],
    }


def test_rank_players_orders_by_composite_score_and_picks_motm(monkeypatch):
    monkeypatch.setattr(scoring_engine, "fetch_fixture", lambda fixture_id: _fake_raw_fixture())

    ranked = scoring_engine.rank_players(999999)

    assert len(ranked) == 4
    scores = [p["composite_score"] for p in ranked]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 10 for s in scores)

    motm = scoring_engine.get_man_of_the_match(999999)
    assert motm["name"] == "Star Striker"


def test_rank_players_excludes_players_with_zero_minutes(monkeypatch):
    raw = _fake_raw_fixture()
    raw["players"][1]["players"].append(
        {
            "player": {"id": 5, "name": "Did Not Play"},
            "statistics": [{"games": {"minutes": None, "position": "M", "rating": None}}],
        }
    )
    monkeypatch.setattr(scoring_engine, "fetch_fixture", lambda fixture_id: raw)

    ranked = scoring_engine.rank_players(999999)
    names = [p["name"] for p in ranked]
    assert "Did Not Play" not in names


# ── Explicabilité du score (Phase 1) ────────────────────────────────────────

@pytest.mark.parametrize(
    "minutes, level",
    [(90, "high"), (60, "high"), (59, "medium"), (30, "medium"), (29, "low"), (0, "low")],
)
def test_score_confidence_tiers(minutes, level):
    conf = scoring_engine.score_confidence(minutes)
    assert conf["level"] == level
    assert conf["minutes"] == minutes
    assert conf["label"]  # libellé non vide


def test_score_contributions_sorted_desc_and_excludes_zeros():
    breakdown = {"goals": 0.30, "tackles": 0.0, "cards_yellow": -0.05, "assists": 0.12}
    contribs = scoring_engine.score_contributions(breakdown)

    values = [c["value"] for c in contribs]
    assert values == sorted(values, reverse=True)           # trié décroissant
    cats = [c["category"] for c in contribs]
    assert "tackles" not in cats                             # les 0 sont masqués
    assert "cards_yellow" in cats                            # le négatif est gardé
    # le libellé lisible est bien mappé
    assert next(c for c in contribs if c["category"] == "goals")["label"] == "buts"


def test_score_contributions_matches_nonzero_breakdown_entries():
    stats = make_stats(position="Defender", tackles=4, interceptions=3, fouls_committed=2, cards_yellow=1)
    result = scoring_engine.compute_player_score(stats, "Defender")
    nonzero = {k for k, v in result["breakdown"].items() if abs(v) > 1e-9}
    assert {c["category"] for c in result["contributions"]} == nonzero


def test_compute_player_score_exposes_confidence_and_contributions():
    result = scoring_engine.compute_player_score(make_stats(minutes=20), "Midfielder")
    assert result["confidence"]["level"] == "low"           # 20 min → faible
    assert isinstance(result["contributions"], list)


def test_rank_players_propagates_explainability(monkeypatch):
    monkeypatch.setattr(scoring_engine, "fetch_fixture", lambda fixture_id: _fake_raw_fixture())
    ranked = scoring_engine.rank_players(999999)
    sub = next(p for p in ranked if p["name"] == "Bench Sub")  # 3 minutes
    assert sub["confidence"]["level"] == "low"
    assert "contributions" in ranked[0]
