from llm import report_generator


def test_events_for_player_matches_by_id_not_abbreviated_name():
    """Régression : l'API-Football renvoie des noms abrégés dans les événements
    ("B. Saka") mais des noms complets dans les scores joueurs ("Bukayo Saka").
    Un rapprochement par nom échouerait silencieusement — on matche par ID."""
    raw_events = [
        {
            "time": {"elapsed": 32, "extra": None},
            "type": "Goal",
            "detail": "Normal Goal",
            "team": {"name": "Arsenal"},
            "player": {"id": 1460, "name": "B. Saka"},
            "assist": {"id": 22090, "name": "W. Saliba"},
        }
    ]
    events_summary = report_generator._summarize_events(raw_events)

    scorer_events = report_generator._events_for_player(events_summary, 1460)
    assert len(scorer_events) == 1
    assert scorer_events[0]["type"] == "Goal"
    # les IDs internes ne doivent pas fuiter dans les données envoyées au LLM
    assert "player_id" not in scorer_events[0]
    assert "assist_id" not in scorer_events[0]

    assist_events = report_generator._events_for_player(events_summary, 22090)
    assert len(assist_events) == 1

    unrelated_events = report_generator._events_for_player(events_summary, 999)
    assert unrelated_events == []


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
    monkeypatch.setattr(report_generator, "fetch_fixture", lambda fixture_id: {"events": []})
    monkeypatch.setattr(report_generator, "_recent_form", lambda player_id, exclude_fixture_id, limit=3: [])

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


def test_generate_match_report_enriches_players_with_events_and_form(tmp_path, monkeypatch):
    monkeypatch.setattr(report_generator, "DATA_PROCESSED_DIR", tmp_path)

    players = [_make_player(1, "Team A"), _make_player(3, "Team B")]
    monkeypatch.setattr(report_generator, "rank_players", lambda fixture_id: players)
    monkeypatch.setattr(
        report_generator,
        "fetch_fixture",
        lambda fixture_id: {
            "events": [
                {
                    "time": {"elapsed": 10, "extra": None},
                    "type": "Goal",
                    "detail": "Normal Goal",
                    "team": {"name": "Team A"},
                    "player": {"id": 1, "name": "Player 1"},
                    "assist": {"id": None, "name": None},
                }
            ]
        },
    )
    monkeypatch.setattr(
        report_generator,
        "_recent_form",
        lambda player_id, exclude_fixture_id, limit=3: (
            [{"fixture_id": 1, "opponent_name": "Other Team", "composite_score": 6.0}]
            if player_id == 1
            else []
        ),
    )

    captured = {}

    def fake_generate_report(prompt):
        if "player_events" in prompt or "match_events" in prompt or "recent_matches" in prompt:
            captured["batch_prompt"] = prompt
        return "[[1]]\nAnalyse 1.\n\n[[3]]\nAnalyse 3." if "Player 1" in prompt else (
            "[[1]]\nTactique A.\n\n[[2]]\nTactique B."
        )

    monkeypatch.setattr(report_generator, "generate_report", fake_generate_report)

    report_generator.generate_match_report(999, force_refresh=True)

    assert "batch_prompt" in captured
    assert "match_events" in captured["batch_prompt"]
    assert "recent_matches" in captured["batch_prompt"]
    assert "Other Team" in captured["batch_prompt"]
