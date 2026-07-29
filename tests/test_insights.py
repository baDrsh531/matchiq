from ml import insights


def _p(name, position, score, team="Home FC", minutes=90, red=0):
    return {
        "name": name,
        "position": position,
        "team_name": team,
        "minutes": minutes,
        "composite_score": score,
        "breakdown": {"cards_red": red},
    }


# ── match_insights ──────────────────────────────────────────────────────────

def test_no_insight_when_too_few_players():
    assert insights.match_insights([]) == []
    assert insights.match_insights([_p("Seul", "Attacker", 8.0)]) == []


def test_motm_gap_insight_fires_on_large_lead():
    ranked = [_p("Star", "Attacker", 10.0), _p("Second", "Midfielder", 7.5)]
    out = insights.match_insights(ranked)
    assert any("Star" in i and "d'avance" in i for i in out)


def test_no_gap_insight_when_scores_are_close():
    ranked = [_p("A", "Attacker", 7.2), _p("B", "Midfielder", 7.0)]
    assert not any("d'avance" in i for i in insights.match_insights(ranked))


def test_defender_motm_ahead_of_attackers():
    ranked = [
        _p("Partey", "Defender", 10.0),
        _p("Saka", "Attacker", 8.0),
        _p("Nketiah", "Attacker", 6.0),
    ]
    out = insights.match_insights(ranked)
    assert any("défenseur" in i and "Partey" in i for i in out)


def test_no_defender_motm_insight_when_motm_is_attacker():
    ranked = [_p("Benzema", "Attacker", 10.0), _p("Vini", "Attacker", 7.0)]
    assert not any("homme du match, devant tous les attaquants" in i for i in insights.match_insights(ranked))


def test_substitute_impact_insight():
    ranked = [
        _p("Star", "Attacker", 10.0),
        _p("Sub", "Attacker", 8.5, minutes=12),
        _p("C", "Midfielder", 6.0),
    ]
    out = insights.match_insights(ranked)
    assert any("Entré en jeu" in i and "Sub" in i for i in out)


def test_team_domination_insight():
    ranked = [
        _p("A1", "Attacker", 9.0, team="Arsenal"),
        _p("A2", "Midfielder", 8.0, team="Arsenal"),
        _p("A3", "Defender", 7.0, team="Arsenal"),
        _p("A4", "Attacker", 6.0, team="Arsenal"),
        _p("B1", "Defender", 5.0, team="Forest"),
    ]
    out = insights.match_insights(ranked)
    assert any("Arsenal" in i and "top 5" in i for i in out)


def test_red_card_insight():
    ranked = [
        _p("Star", "Attacker", 9.0),
        _p("Fouler", "Defender", 7.0, red=-0.2),
        _p("C", "Midfielder", 5.0),
    ]
    out = insights.match_insights(ranked)
    assert any("expulsé" in i and "Fouler" in i for i in out)


def test_insights_capped_at_four():
    ranked = [
        _p("Partey", "Defender", 10.0, team="Arsenal", red=-0.2),
        _p("Sub", "Attacker", 8.4, team="Arsenal", minutes=10),
        _p("A3", "Midfielder", 8.0, team="Arsenal"),
        _p("A4", "Attacker", 7.5, team="Arsenal"),
        _p("B1", "Attacker", 5.0, team="Forest"),
    ]
    assert len(insights.match_insights(ranked)) <= 4


# ── form_summary ────────────────────────────────────────────────────────────

def _m(score, opponent="Adv", fixture=1):
    return {"composite_score": score, "opponent_name": opponent, "fixture_id": fixture}


def test_form_summary_none_when_empty():
    assert insights.form_summary([]) is None


def test_form_summary_single_match():
    form = insights.form_summary([_m(7.0)])
    assert form["trend"] == "single"
    assert form["best"] is None


def test_form_summary_progression():
    form = insights.form_summary([_m(5.0, "A"), _m(6.5, "B"), _m(8.0, "C")])
    assert form["trend"] == "up"
    assert form["label"] == "En progression"
    assert form["best"]["score"] == 8.0
    assert form["worst"]["score"] == 5.0


def test_form_summary_decline():
    form = insights.form_summary([_m(8.0), _m(6.0), _m(4.5)])
    assert form["trend"] == "down"


def test_form_summary_stable_and_consistency():
    form = insights.form_summary([_m(6.2), _m(6.5), _m(6.0)])
    assert form["trend"] == "stable"
    assert form["consistency"] == "régulier"
