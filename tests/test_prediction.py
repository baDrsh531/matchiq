"""Tests du service de prédiction (ingestion mockée, aucun appel réseau)."""
import pytest

import ml.prediction as prediction


def _fx(fid, hid, aid, hg, ag, date, hname, aname, status="FT"):
    return {
        "fixture": {"id": fid, "date": date, "status": {"short": status}},
        "teams": {"home": {"id": hid, "name": hname}, "away": {"id": aid, "name": aname}},
        "goals": {"home": hg, "away": ag},
    }


@pytest.fixture
def league(monkeypatch):
    # Petite ligue à 3 équipes, aller-retour, où 10 (fort) > 20 (moyen) > 30 (faible).
    fixtures = [
        _fx(1, 10, 30, 3, 0, "2023-01-05", "Fort", "Faible"),
        _fx(2, 20, 30, 2, 0, "2023-01-12", "Moyen", "Faible"),
        _fx(3, 10, 20, 2, 0, "2023-01-19", "Fort", "Moyen"),
        _fx(4, 30, 10, 0, 2, "2023-02-05", "Faible", "Fort"),
        _fx(5, 30, 20, 0, 1, "2023-02-12", "Faible", "Moyen"),
        _fx(6, 20, 10, 0, 1, "2023-02-19", "Moyen", "Fort"),
        # un match "à venir" non joué, pour predict_fixture sans résultat
        _fx(99, 10, 30, None, None, "2023-03-01", "Fort", "Faible", status="NS"),
    ]
    monkeypatch.setattr(prediction, "fetch_league_fixtures", lambda lg, s, **k: fixtures)
    prediction._model_cache.clear()
    prediction._brier_cache.clear()
    return fixtures


def test_matchup_by_name_favors_stronger(league):
    p = prediction.predict_matchup(61, 2023, "Fort", "Faible")
    assert p["home"] > p["away"]
    assert p["home_name"] == "Fort" and p["away_name"] == "Faible"
    assert abs(p["home"] + p["draw"] + p["away"] - 1.0) < 1e-6


def test_matchup_by_id(league):
    p = prediction.predict_matchup(61, 2023, 10, 20)
    assert p["rating_home"] > p["rating_away"]


def test_matchup_unknown_team_raises(league):
    with pytest.raises(ValueError):
        prediction.predict_matchup(61, 2023, "Fort", "Inexistante")


def test_predict_fixture_trains_only_on_past(league):
    # Match 6 (2023-02-19) : le modèle ne doit voir que les 5 matchs antérieurs.
    p = prediction.predict_fixture(61, 2023, 6)
    assert p["trained_on"] == 5
    assert p["result"]["outcome"] == "away"      # Fort gagne à l'extérieur (0-1)
    assert "hit" in p["result"]
    assert 0.0 <= p["result"]["prob_of_actual"] <= 1.0


def test_predict_fixture_unplayed_has_no_result(league):
    p = prediction.predict_fixture(61, 2023, 99)
    assert "result" not in p
    assert p["home_name"] == "Fort"


def test_predict_fixture_missing_raises(league):
    with pytest.raises(ValueError):
        prediction.predict_fixture(61, 2023, 123456)


def test_list_cached_comments_filters_and_sorts(tmp_path, monkeypatch):
    import json as _json

    from llm import report_generator as rg

    monkeypatch.setattr(rg, "DATA_PROCESSED_DIR", tmp_path)

    def _write(name, hit, date):
        (tmp_path / name).write_text(_json.dumps(
            {"comment": name, "prediction": {"date": date, "result": {"hit": hit}}}
        ), encoding="utf-8")

    _write("predict_61_2023_1.json", True, "2023-05-01")     # FR, juste
    _write("predict_61_2023_2.json", False, "2023-04-01")    # FR, surprise
    _write("predict_61_2023_3_en.json", True, "2023-03-01")  # EN -> exclu en FR
    _write("predict_99_2023_9.json", True, "2023-02-01")     # autre ligue -> exclu

    fr = rg.list_cached_prediction_comments(61, 2023, "fr")
    assert [c["comment"] for c in fr] == ["predict_61_2023_2.json", "predict_61_2023_1.json"]  # surprise d'abord
    en = rg.list_cached_prediction_comments(61, 2023, "en")
    assert [c["comment"] for c in en] == ["predict_61_2023_3_en.json"]


def test_league_table_sorted_with_calibration(league):
    table = prediction.league_table(61, 2023)
    names = [t["name"] for t in table["teams"]]
    assert names[0] == "Fort"          # meilleure note en tête
    assert names[-1] == "Faible"
    assert table["calibration"]["n"] == 6      # 6 matchs joués (le 7e est NS)
    assert "brier" in table["calibration"]
