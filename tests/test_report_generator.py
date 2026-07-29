import pytest

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

    def fake_generate_report(prompt, lang="fr"):
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

    def fake_generate_report(prompt, lang="fr"):
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


# ── Q&R ancrée sur un match (Phase 2) ───────────────────────────────────────

def _fake_ranked():
    return [
        {
            "player_id": 1, "name": "Star", "team_name": "Home FC", "position": "Attacker",
            "minutes": 90, "composite_score": 10.0,
            "contributions": [{"category": "goals", "label": "buts", "value": 0.4}],
            "strengths": ["buts"], "weaknesses": [],
        },
        {
            "player_id": 2, "name": "Keeper", "team_name": "Away FC", "position": "Goalkeeper",
            "minutes": 90, "composite_score": 6.0,
            "contributions": [], "strengths": ["arrêts"], "weaknesses": [],
        },
    ]


def _patch_qa_context(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "DATA_PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(report_generator, "rank_players", lambda fid: _fake_ranked())
    monkeypatch.setattr(report_generator, "fetch_fixture", lambda fid: {"events": []})
    monkeypatch.setattr(
        report_generator, "build_match_summary",
        lambda fid, raw: {
            "teams": {"home": {"name": "Home FC"}, "away": {"name": "Away FC"}},
            "goals": {"home": 2, "away": 1},
        },
    )


def test_answer_match_question_grounds_prompt_and_caches(tmp_path, monkeypatch):
    _patch_qa_context(monkeypatch, tmp_path)
    calls = {"n": 0}

    def fake_gen(prompt, lang="fr"):
        calls["n"] += 1
        # ancrage : les données calculées ET la question sont dans le prompt
        assert "Star" in prompt and "composite_score" in prompt
        assert "meilleure note" in prompt
        return "Star a dominé le match."

    monkeypatch.setattr(report_generator, "generate_report", fake_gen)

    r1 = report_generator.answer_match_question(999, "Qui a la meilleure note ?")
    assert r1["answer"] == "Star a dominé le match."
    assert calls["n"] == 1

    # même question (casse / espaces différents) → cache, aucun nouvel appel LLM
    r2 = report_generator.answer_match_question(999, "  QUI a   la meilleure note ? ")
    assert r2["answer"] == "Star a dominé le match."
    assert calls["n"] == 1


def test_answer_match_question_unknown_fixture_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(report_generator, "DATA_PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(report_generator, "rank_players", lambda fid: [])
    with pytest.raises(ValueError):
        report_generator.answer_match_question(999, "une question")


def test_normalize_question_is_stable_across_casing_and_spacing():
    a = report_generator._normalize_question("Pourquoi ?")
    b = report_generator._normalize_question("  pourquoi   ? ")
    c = report_generator._normalize_question("Une autre question")
    assert a == b
    assert a != c


# ── Rapports bilingues (Phase 4) ────────────────────────────────────────────

def test_system_prompt_language_directive():
    from llm import prompt_templates
    fr = prompt_templates.system_prompt("fr")
    en = prompt_templates.system_prompt("en")
    assert "français" in fr
    assert "English" in en
    # la base anti-hallucination est commune aux deux langues
    assert "JAMAIS inventer" in fr and "JAMAIS inventer" in en


def test_report_cache_path_backward_compatible_for_fr():
    assert report_generator._report_cache_path(999, "fr").name == "999_report.json"
    assert report_generator._report_cache_path(999, "en").name == "999_report_en.json"
    assert report_generator._qa_cache_path(999, "abc", "fr").name == "999_qa_abc.json"
    assert report_generator._qa_cache_path(999, "abc", "en").name == "999_qa_abc_en.json"


def test_answer_match_question_caches_per_language(tmp_path, monkeypatch):
    _patch_qa_context(monkeypatch, tmp_path)
    seen = []

    def fake_gen(prompt, lang="fr"):
        seen.append(lang)
        return f"answer-{lang}"

    monkeypatch.setattr(report_generator, "generate_report", fake_gen)

    assert report_generator.answer_match_question(999, "Question ?", lang="fr")["answer"] == "answer-fr"
    assert report_generator.answer_match_question(999, "Question ?", lang="en")["answer"] == "answer-en"
    assert seen == ["fr", "en"]  # deux langues = deux générations distinctes

    # re-demander en français relit le cache FR : pas de 3ᵉ appel
    report_generator.answer_match_question(999, "Question ?", lang="fr")
    assert seen == ["fr", "en"]
