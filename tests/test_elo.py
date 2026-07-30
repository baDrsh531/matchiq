"""Tests du modèle Elo (déterministe, sans appel réseau)."""
from ml.elo import (
    BASE_RATING,
    EloModel,
    brier_score,
    expected_score,
    update_ratings,
    win_draw_loss,
)


def _fx(hid, aid, hg, ag, date, hname="H", aname="A", status="FT"):
    return {
        "fixture": {"date": date, "status": {"short": status}},
        "teams": {"home": {"id": hid, "name": hname}, "away": {"id": aid, "name": aname}},
        "goals": {"home": hg, "away": ag},
    }


# ── Espérance de points ──────────────────────────────────────────────────────

def test_expected_score_symmetric_without_home_advantage():
    # À force égale et sans avantage terrain, l'espérance est exactement 0,5.
    assert abs(expected_score(1500, 1500, home_advantage=0) - 0.5) < 1e-9


def test_home_advantage_pushes_expectation_above_half():
    assert expected_score(1500, 1500) > 0.5


def test_stronger_team_has_higher_expectation():
    assert expected_score(1800, 1500, home_advantage=0) > 0.75


# ── Mise à jour des notes ────────────────────────────────────────────────────

def test_update_conserves_total_points():
    rh, ra = update_ratings(1500, 1500, 2, 0)
    assert abs((rh + ra) - 3000) < 1e-9  # ce que l'un gagne, l'autre le perd


def test_winner_gains_loser_loses():
    rh, ra = update_ratings(1500, 1500, 3, 1)
    assert rh > 1500 and ra < 1500


def test_upset_moves_more_than_expected_win():
    # Le favori qui gagne bouge peu ; l'outsider qui gagne bouge beaucoup.
    fav_win_h, _ = update_ratings(1800, 1500, 1, 0)
    _, upset_win_a = update_ratings(1800, 1500, 0, 1)
    gain_favori = fav_win_h - 1800
    gain_outsider = upset_win_a - 1500
    assert gain_outsider > gain_favori


# ── Modèle de nul (V/N/D) ────────────────────────────────────────────────────

def test_win_draw_loss_sums_to_one():
    for e in (0.1, 0.3, 0.5, 0.7, 0.95):
        h, d, a = win_draw_loss(e)
        assert abs(h + d + a - 1.0) < 1e-9


def test_draw_is_maximal_at_balance():
    _, d_bal, _ = win_draw_loss(0.5)
    _, d_skew, _ = win_draw_loss(0.85)
    assert d_bal > d_skew


def test_probabilities_never_negative_at_extremes():
    for e in (0.0, 0.01, 0.99, 1.0):
        h, d, a = win_draw_loss(e)
        assert h >= 0 and d >= 0 and a >= 0


def test_expectation_identity_preserved():
    # P(victoire) + 0,5·P(nul) doit redonner l'espérance E.
    for e in (0.35, 0.5, 0.72):
        h, d, _ = win_draw_loss(e)
        assert abs((h + 0.5 * d) - e) < 1e-6


# ── EloModel : fit + predict ─────────────────────────────────────────────────

def test_fit_orders_by_date_and_rates_dominant_team_higher():
    # L'équipe 1 gagne tous ses matchs -> sa note doit finir la plus haute.
    fixtures = [
        _fx(1, 2, 2, 0, "2023-01-10", hname="Un", aname="Deux"),
        _fx(1, 3, 3, 1, "2023-02-10", hname="Un", aname="Trois"),
        _fx(3, 2, 1, 1, "2023-03-10", hname="Trois", aname="Deux"),
        _fx(2, 1, 0, 2, "2023-04-10", hname="Deux", aname="Un"),
    ]
    model = EloModel().fit(fixtures)
    assert model.rating(1) > model.rating(3)
    assert model.rating(1) > model.rating(2)
    assert model.names[1] == "Un"
    assert model.games[1] == 3


def test_fit_ignores_unfinished_matches():
    model = EloModel().fit([_fx(1, 2, 0, 0, "2023-01-10", status="NS")])
    assert model.rating(1) == BASE_RATING
    assert model.games.get(1, 0) == 0


def test_predict_favors_higher_rated_home_team():
    fixtures = [_fx(1, 2, 3, 0, f"2023-0{i}-10") for i in range(1, 6)]
    model = EloModel().fit(fixtures)
    proba = model.predict(1, 2)
    assert proba["home"] > proba["away"]
    assert proba["rating_diff"] > 0
    assert abs(proba["home"] + proba["draw"] + proba["away"] - 1.0) < 1e-6


def test_predict_unknown_teams_are_even():
    proba = EloModel().predict(99, 98)  # jamais vues -> base identique
    assert proba["home"] > proba["away"]        # seul l'avantage terrain joue
    assert proba["rating_diff"] == 0.0


# ── Score de Brier (calibration walk-forward) ────────────────────────────────

def test_brier_returns_none_on_empty():
    res = brier_score([])
    assert res["n"] == 0 and res["brier"] is None


def test_brier_beats_baseline_on_predictable_league():
    # Équipe 1 = forte, 2 = moyenne, 3 = faible. Chaque duel se joue À DOMICILE ET
    # À L'EXTÉRIEUR : les résultats mélangent donc victoires domicile et extérieur,
    # si bien que la baseline « toujours les taux moyens » n'est PAS triviale. Sur
    # cette structure apprenable, l'Elo (qui suit la force) doit faire mieux.
    fixtures = []
    for m in range(1, 7):
        d = f"2023-{m:02d}"
        fixtures += [
            _fx(1, 3, 3, 0, f"{d}-01"),   # fort bat faible (dom)
            _fx(3, 1, 0, 2, f"{d}-05"),   # fort gagne à l'extérieur
            _fx(2, 3, 2, 0, f"{d}-10"),   # moyen bat faible (dom)
            _fx(3, 2, 0, 1, f"{d}-15"),   # moyen gagne à l'extérieur
            _fx(1, 2, 2, 0, f"{d}-20"),   # fort bat moyen (dom)
            _fx(2, 1, 0, 1, f"{d}-25"),   # fort gagne à l'extérieur
        ]
    res = brier_score(fixtures)
    assert res["n"] == 36
    assert 0.0 <= res["brier"] <= 2.0
    assert res["skill"] > 0  # mieux que « toujours les taux moyens »
