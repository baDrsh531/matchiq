"""Tests du clustering d'équipes (k-means déterministe, numpy)."""
import numpy as np

from ml.clustering import cluster_teams, extract_team_features, kmeans


def _stat(type_, value):
    return {"type": type_, "value": value}


def _fixture(team_id, name, possession, shots):
    return {
        "statistics": [
            {"team": {"id": team_id, "name": name},
             "statistics": [_stat("Ball Possession", possession), _stat("Total Shots", shots)]}
        ]
    }


# ── Extraction des features ──────────────────────────────────────────────────

def test_extract_parses_percent_and_averages():
    fixtures = [_fixture(1, "A", "60%", 15), _fixture(1, "A", "50%", 11)]
    feats = extract_team_features(fixtures)
    assert len(feats) == 1
    a = feats[0]
    assert a["matches"] == 2
    assert a["features"]["possession"] == 55.0        # (60+50)/2, "%" nettoyé
    assert a["features"]["volume de tirs"] == 13.0


def test_extract_ignores_unknown_stats():
    fx = {"statistics": [{"team": {"id": 1, "name": "A"},
                          "statistics": [_stat("Ball Possession", "50%"), _stat("Expected Goals", "1.2")]}]}
    feats = extract_team_features([fx])
    assert "possession" in feats[0]["features"]
    assert all("xg" not in k.lower() for k in feats[0]["features"])


# ── k-means pur ──────────────────────────────────────────────────────────────

def test_kmeans_separates_two_obvious_groups():
    z = np.array([[0.0, 0.0], [0.1, 0.1], [5.0, 5.0], [5.1, 4.9]])
    labels, centroids = kmeans(z, 2)
    assert labels[0] == labels[1]        # les deux points proches ensemble
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]        # séparés de l'autre groupe


def test_kmeans_is_deterministic():
    z = np.random.RandomState(0).rand(12, 3)
    a, _ = kmeans(z, 3)
    b, _ = kmeans(z, 3)
    assert np.array_equal(a, b)          # aucun aléa : même résultat


# ── cluster_teams (bout en bout) ─────────────────────────────────────────────

def _team(tid, name, possession, shots):
    return {"team_id": tid, "name": name, "matches": 1,
            "features": {"possession": possession, "volume de tirs": shots}}


def test_cluster_teams_needs_enough_teams():
    res = cluster_teams([_team(1, "A", 60, 12)], k=3)
    assert res["enough_data"] is False


def test_cluster_teams_groups_similar_styles():
    teams = [
        _team(1, "PossA", 65, 10), _team(2, "PossB", 63, 11),   # possession
        _team(3, "DirectA", 40, 20), _team(4, "DirectB", 42, 19),  # jeu direct
    ]
    res = cluster_teams(teams, k=2)
    assert res["enough_data"] is True
    # les deux équipes de possession doivent tomber dans le même cluster
    cluster_of = {}
    for ci, cl in enumerate(res["clusters"]):
        for t in cl["teams"]:
            cluster_of[t["name"]] = ci
    assert cluster_of["PossA"] == cluster_of["PossB"]
    assert cluster_of["DirectA"] == cluster_of["DirectB"]
    assert cluster_of["PossA"] != cluster_of["DirectA"]


def test_cluster_label_names_dominant_axis():
    teams = [
        _team(1, "A", 70, 8), _team(2, "B", 68, 9),
        _team(3, "C", 35, 22), _team(4, "D", 33, 21),
    ]
    res = cluster_teams(teams, k=2)
    labels = " ".join(c["label"] for c in res["clusters"])
    assert "possession" in labels or "volume de tirs" in labels
