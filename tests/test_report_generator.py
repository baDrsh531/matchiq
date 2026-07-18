from llm import report_generator


def test_parse_batch_blocks_extracts_each_key():
    text = (
        "[[101]]\nAnalyse du joueur 101.\n\n"
        "[[202]]\nAnalyse du joueur 202, multi-ligne.\nDeuxième ligne.\n\n"
        "[[303]]\nAnalyse du joueur 303."
    )
    result = report_generator._parse_batch_blocks(
        text, ["101", "202", "303"], fallback="MANQUANT"
    )
    assert result["101"] == "Analyse du joueur 101."
    assert result["202"] == "Analyse du joueur 202, multi-ligne.\nDeuxième ligne."
    assert result["303"] == "Analyse du joueur 303."


def test_parse_batch_blocks_falls_back_on_missing_key():
    text = "[[101]]\nAnalyse du joueur 101."
    result = report_generator._parse_batch_blocks(
        text, ["101", "999"], fallback="MANQUANT"
    )
    assert result["101"] == "Analyse du joueur 101."
    assert result["999"] == "MANQUANT"


def test_parse_batch_blocks_falls_back_on_empty_content():
    text = "[[101]]\n\n[[202]]\nAnalyse valide."
    result = report_generator._parse_batch_blocks(
        text, ["101", "202"], fallback="MANQUANT"
    )
    assert result["101"] == "MANQUANT"
    assert result["202"] == "Analyse valide."


def _make_player(player_id, team_name="Team A"):
    return {
        "player_id": player_id,
        "name": f"Player {player_id}",
        "team_id": 1,
        "team_name": team_name,
        "position": "Midfielder",
        "minutes": 90,
        "composite_score": 5.0,
        "breakdown": {},
        "radar": {},
        "strengths": [],
        "weaknesses": [],
    }


def test_generate_match_report_makes_exactly_three_llm_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(report_generator, "DATA_PROCESSED_DIR", tmp_path)

    players = [
        _make_player(1, "Team A"),
        _make_player(2, "Team A"),
        _make_player(3, "Team B"),
    ]
    monkeypatch.setattr(report_generator, "rank_players", lambda fixture_id: players)

    calls = []

    def fake_generate_report(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return "Rapport MOTM."
        if len(calls) == 2:
            return "[[1]]\nAnalyse 1.\n\n[[2]]\nAnalyse 2.\n\n[[3]]\nAnalyse 3."
        return "[[1]]\nTactique équipe A.\n\n[[2]]\nTactique équipe B."

    monkeypatch.setattr(report_generator, "generate_report", fake_generate_report)

    report = report_generator.generate_match_report(999, force_refresh=True)

    assert len(calls) == 3
    assert report["motm_report"] == "Rapport MOTM."
    assert report["player_reports"] == {
        "1": "Analyse 1.",
        "2": "Analyse 2.",
        "3": "Analyse 3.",
    }
    assert report["tactical_suggestions"] == {
        "Team A": "Tactique équipe A.",
        "Team B": "Tactique équipe B.",
    }
    assert (tmp_path / "999_report.json").exists()
