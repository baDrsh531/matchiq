"""Tests de la détection d'écarts de performance (déterministe)."""
from ml.anomalies import detect_anomalies


def _m(fid, score, opp="Adv", date=None):
    return {"fixture_id": fid, "composite_score": score, "opponent_name": opp,
            "date": date or f"2023-01-{fid:02d}"}


def test_not_enough_data_below_threshold():
    res = detect_anomalies([_m(1, 6.0), _m(2, 7.0)])
    assert res["enough_data"] is False
    assert res["anomalies"] == []


def test_regular_player_has_no_anomaly():
    # Notes quasi constantes -> aucun écart marquant.
    res = detect_anomalies([_m(i, 6.0) for i in range(1, 6)])
    assert res["enough_data"] is True
    assert res["anomalies"] == []


def test_flags_exceptional_high_as_record():
    # 4 matchs autour de 6, un match à 9 -> record perso.
    matches = [_m(1, 6.0), _m(2, 5.8), _m(3, 6.2), _m(4, 5.9), _m(5, 9.2)]
    res = detect_anomalies(matches)
    records = [a for a in res["anomalies"] if a["type"] == "record"]
    assert len(records) == 1
    assert records[0]["fixture_id"] == 5
    assert records[0]["z"] > 0 and records[0]["delta"] > 0


def test_flags_collapse_as_counter_performance():
    matches = [_m(1, 7.5), _m(2, 7.2), _m(3, 7.8), _m(4, 7.4), _m(5, 3.0)]
    res = detect_anomalies(matches)
    bad = [a for a in res["anomalies"] if a["type"] == "contre-performance"]
    assert len(bad) == 1 and bad[0]["fixture_id"] == 5
    assert bad[0]["z"] < 0


def test_latest_alert_set_when_last_match_is_anomaly():
    matches = [_m(1, 6.0), _m(2, 6.1), _m(3, 5.9), _m(4, 9.5)]  # dernier = record
    res = detect_anomalies(matches)
    assert res["latest_alert"] is not None
    assert res["latest_alert"]["fixture_id"] == 4


def test_latest_alert_none_when_last_match_normal():
    matches = [_m(1, 9.5), _m(2, 6.0), _m(3, 6.1), _m(4, 5.9)]  # record au début
    res = detect_anomalies(matches)
    assert res["latest_alert"] is None
    assert any(a["fixture_id"] == 1 for a in res["anomalies"])


def test_baseline_reported():
    res = detect_anomalies([_m(i, 6.0) for i in range(1, 5)])
    assert res["baseline"]["n"] == 4
    assert res["baseline"]["mean"] == 6.0
    assert res["baseline"]["std"] == 0.0


def test_anomalies_sorted_by_magnitude():
    matches = [_m(1, 6.0), _m(2, 6.0), _m(3, 6.0), _m(4, 9.0), _m(5, 1.0)]
    res = detect_anomalies(matches)
    zs = [abs(a["z"]) for a in res["anomalies"]]
    assert zs == sorted(zs, reverse=True)  # la plus forte d'abord
