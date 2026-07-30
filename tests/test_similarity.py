"""Tests de la similarité de joueurs (déterministe, numpy)."""
from ml.similarity import similar_players


def _p(pid, name, breakdown, pos="Defender", score=6.0):
    return {"player_id": pid, "name": name, "position": pos, "average_score": score,
            "appearances": 1, "photo_url": None, "team_id": 1, "team_name": "T",
            "breakdown": breakdown}


def test_returns_empty_for_unknown_target():
    profiles = [_p(1, "A", {"tackles": 5}), _p(2, "B", {"tackles": 3})]
    assert similar_players(999, profiles) == []


def test_returns_empty_when_pool_too_small():
    assert similar_players(1, [_p(1, "A", {"tackles": 5})]) == []


def test_closest_profile_ranks_first():
    # Cible = défenseur "tacleur". Un clone doit passer devant un profil opposé.
    target = _p(1, "Cible", {"tackles": 9, "interceptions": 8, "passes_accuracy": 3})
    clone = _p(2, "Clone", {"tackles": 8, "interceptions": 9, "passes_accuracy": 3})
    opposite = _p(3, "Passeur", {"tackles": 2, "interceptions": 1, "passes_accuracy": 9})
    other = _p(4, "Neutre", {"tackles": 5, "interceptions": 5, "passes_accuracy": 5})
    res = similar_players(1, [target, clone, opposite, other])
    assert res[0]["player_id"] == 2                 # le clone en tête
    assert res[0]["similarity"] > res[-1]["similarity"]
    assert -1.0 <= res[0]["similarity"] <= 1.0


def test_excludes_target_from_results():
    profiles = [_p(i, f"P{i}", {"tackles": i, "interceptions": 10 - i}) for i in range(1, 6)]
    res = similar_players(3, profiles)
    assert all(r["player_id"] != 3 for r in res)


def test_limit_is_respected():
    profiles = [_p(i, f"P{i}", {"tackles": i, "interceptions": 10 - i}) for i in range(1, 10)]
    assert len(similar_players(1, profiles, limit=3)) == 3


def test_similarity_symmetric_pair():
    # Deux joueurs, la proximité de 1->2 doit égaler celle de 2->1.
    profiles = [
        _p(1, "A", {"tackles": 8, "interceptions": 2}),
        _p(2, "B", {"tackles": 3, "interceptions": 7}),
        _p(3, "C", {"tackles": 5, "interceptions": 5}),
    ]
    s12 = similar_players(1, profiles)
    s21 = similar_players(2, profiles)
    sim_1_to_2 = next(r["similarity"] for r in s12 if r["player_id"] == 2)
    sim_2_to_1 = next(r["similarity"] for r in s21 if r["player_id"] == 1)
    assert abs(sim_1_to_2 - sim_2_to_1) < 1e-9
