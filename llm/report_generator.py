"""Orchestration : scores ML -> prompts -> LLM -> rapport structuré.

Les rapports générés sont mis en cache sur disque (data/processed/) pour
éviter de regénérer un rapport à chaque appel API et donc de gaspiller des
tokens LLM.

Le rapport complet (tous les joueurs + tactique) est généré via 3 appels LLM
batchés (1 MOTM + 1 pour tous les joueurs + 1 pour les deux équipes) plutôt
qu'un appel par joueur/équipe : sur un match à 30 joueurs ça remplace ~33
appels séquentiels par 3, ce qui évite de saturer les limites de requêtes/
minute des plans LLM gratuits.

Chaque prompt est enrichi (gratuitement, données déjà en cache/DB) avec :
- le déroulé du match (buts, cartons, changements) pour le rapport MOTM et
  les analyses joueurs, afin de relier les stats au récit du match ;
- la forme récente du joueur (matchs précédents déjà analysés, via la DB)
  pour commenter une tendance plutôt qu'un match isolé.
"""
import hashlib
import json
import re
from pathlib import Path

from config import DATA_PROCESSED_DIR
from llm.llm_client import generate_report
from llm.prompt_templates import (
    batch_player_analysis_prompt,
    batch_tactical_suggestions_prompt,
    match_qa_prompt,
    motm_report_prompt,
    player_analysis_prompt,
)
from ml.ingestion import build_match_summary, fetch_fixture
from ml.insights import match_insights
from ml.scoring_engine import rank_players
from persistence.database import SessionLocal
from persistence.repository import get_player_history


def _lang_suffix(lang: str) -> str:
    # Le français garde le nom d'origine (rétro-compatibilité des caches déjà
    # présents dans demo_data/) ; les autres langues ont leur propre fichier.
    return "" if lang == "fr" else f"_{lang}"


def _report_cache_path(fixture_id: int, lang: str = "fr") -> Path:
    return DATA_PROCESSED_DIR / f"{fixture_id}_report{_lang_suffix(lang)}.json"


def _player_analysis_cache_path(fixture_id: int, player_id: int, lang: str = "fr") -> Path:
    return DATA_PROCESSED_DIR / f"{fixture_id}_player_{player_id}{_lang_suffix(lang)}.json"


def _qa_cache_path(fixture_id: int, question_key: str, lang: str = "fr") -> Path:
    return DATA_PROCESSED_DIR / f"{fixture_id}_qa_{question_key}{_lang_suffix(lang)}.json"


def _prediction_comment_cache_path(league_id: int, season: int, fixture_id: int,
                                   lang: str = "fr") -> Path:
    return DATA_PROCESSED_DIR / f"predict_{league_id}_{season}_{fixture_id}{_lang_suffix(lang)}.json"


def comment_prediction(league_id: int, season: int, fixture_id: int,
                       force_refresh: bool = False, lang: str = "fr") -> dict:
    """Prédiction pré-match Elo + commentaire LLM, mis en cache (comme les rapports).

    Le pronostic est déterministe (module ml.prediction) ; le LLM ne fait que le
    commenter face au résultat réel. En mode démo, seul le cache répond."""
    from ml.prediction import predict_fixture
    from llm.prompt_templates import prediction_comment_prompt

    cache = _prediction_comment_cache_path(league_id, season, fixture_id, lang)
    if cache.exists() and not force_refresh:
        return json.loads(cache.read_text(encoding="utf-8"))

    prediction = predict_fixture(league_id, season, fixture_id)
    comment = generate_report(prediction_comment_prompt(prediction), lang=lang)
    result = {"league_id": league_id, "season": season, "fixture_id": fixture_id,
              "lang": lang, "prediction": prediction, "comment": comment}
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _normalize_question(question: str) -> str:
    """Clé de cache stable : deux formulations identiques à la casse / aux
    espaces près partagent la même réponse (et donc un seul appel LLM)."""
    canonical = " ".join(question.strip().lower().split())
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]


def _parse_batch_blocks(text: str, keys: list[str], fallback: str) -> dict[str, str]:
    """Parse un texte formaté en blocs `[[clé]]\ncontenu` (voir prompt_templates).

    Robuste aux réponses imparfaites du LLM : toute clé attendue mais absente
    (ou vide) du texte reçoit `fallback` plutôt que de faire planter le rapport.
    """
    parts = re.split(r"\[\[\s*([^\[\]]+?)\s*\]\]", text)
    parsed: dict[str, str] = {}
    for i in range(1, len(parts), 2):
        key = parts[i].strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if content:
            parsed[key] = content

    return {key: parsed.get(key, fallback) for key in keys}


def _summarize_events(raw_events: list[dict] | None) -> list[dict]:
    """Réduit les événements bruts de l'API-Football aux champs utiles au LLM.

    Garde `player_id`/`assist_id` (int) pour un rapprochement fiable avec les
    scores joueurs : les événements utilisent des noms abrégés (ex: "B. Saka")
    alors que les scores utilisent le nom complet ("Bukayo Saka") — comparer
    les IDs plutôt que les chaînes évite un rapprochement silencieusement raté.
    """
    summary = []
    for e in raw_events or []:
        time = e.get("time") or {}
        minute = time.get("elapsed")
        extra = time.get("extra")
        player = e.get("player") or {}
        assist = e.get("assist") or {}
        summary.append(
            {
                "minute": f"{minute}+{extra}" if extra else minute,
                "type": e.get("type"),
                "detail": e.get("detail"),
                "team": (e.get("team") or {}).get("name"),
                "player": player.get("name"),
                "player_id": player.get("id"),
                "assist": assist.get("name"),
                "assist_id": assist.get("id"),
            }
        )
    return summary


def _events_for_player(events_summary: list[dict], player_id: int) -> list[dict]:
    """Événements impliquant ce joueur (buteur ou passeur), par ID exact.

    Renvoie des événements "nettoyés" (sans les IDs internes, non pertinents
    pour le LLM)."""
    matched = [e for e in events_summary if player_id in (e.get("player_id"), e.get("assist_id"))]
    return [{k: v for k, v in e.items() if k not in ("player_id", "assist_id")} for e in matched]


def _recent_form(player_id: int, exclude_fixture_id: int, limit: int = 3) -> list[dict]:
    """Derniers matchs déjà analysés pour ce joueur (hors match courant),
    pour donner au LLM une tendance plutôt qu'un instantané isolé."""
    session = SessionLocal()
    try:
        history = get_player_history(session, player_id)
    finally:
        session.close()

    if not history:
        return []
    matches = [m for m in history["matches"] if m["fixture_id"] != exclude_fixture_id]
    return matches[-limit:]


def get_player_analysis(
    fixture_id: int, player_id: int, force_refresh: bool = False, lang: str = "fr"
) -> dict:
    """Retourne le score ML + l'analyse LLM d'un joueur, avec mise en cache par langue."""
    ranked_players = rank_players(fixture_id)
    player = next((p for p in ranked_players if p["player_id"] == player_id), None)
    if player is None:
        raise ValueError(f"Joueur {player_id} introuvable pour le fixture {fixture_id}.")

    cache_file = _player_analysis_cache_path(fixture_id, player_id, lang)
    if cache_file.exists() and not force_refresh:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        cached["score"] = player
        return cached

    raw = fetch_fixture(fixture_id)
    events_summary = _summarize_events(raw.get("events"))
    player_events = _events_for_player(events_summary, player_id)
    recent_matches = _recent_form(player_id, exclude_fixture_id=fixture_id)

    analysis = generate_report(
        player_analysis_prompt(
            player,
            recent_matches=recent_matches or None,
            player_events=player_events or None,
        ),
        lang=lang,
    )
    result = {"score": player, "analysis": analysis}

    cache_file.write_text(
        json.dumps({"analysis": analysis}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def _match_qa_context(fixture_id: int) -> dict:
    """Contexte compact d'un match pour la Q&R : uniquement des données déjà
    calculées/en cache (scores, contributions, déroulé). Aucun appel LLM ici."""
    ranked = rank_players(fixture_id)
    if not ranked:
        raise ValueError(f"Aucun joueur trouvé pour le fixture {fixture_id}.")

    raw = fetch_fixture(fixture_id)
    summary = build_match_summary(fixture_id, raw)

    players = [
        {
            "name": p["name"],
            "team": p["team_name"],
            "position": p["position"],
            "minutes": p["minutes"],
            "composite_score": p["composite_score"],
            "top_contributions": p.get("contributions", [])[:4],
            "strengths": p["strengths"],
            "weaknesses": p["weaknesses"],
        }
        for p in ranked
    ]
    return {
        "teams": summary.get("teams"),
        "goals": summary.get("goals"),
        "man_of_the_match": ranked[0]["name"],
        "players": players,
        "events": _summarize_events(raw.get("events")),
    }


def answer_match_question(
    fixture_id: int, question: str, force_refresh: bool = False, lang: str = "fr"
) -> dict:
    """Répond à une question en langage naturel sur un match, en s'appuyant
    uniquement sur les scores/stats déjà calculés (LLM ancré, anti-hallucination).

    La réponse est mise en cache par (match, question normalisée, langue) :
    reposer la même question ne consomme aucun nouveau token LLM.
    """
    question = question.strip()
    cache_file = _qa_cache_path(fixture_id, _normalize_question(question), lang)
    if cache_file.exists() and not force_refresh:
        return json.loads(cache_file.read_text(encoding="utf-8"))

    context = _match_qa_context(fixture_id)
    answer = generate_report(match_qa_prompt(question, context), lang=lang)
    result = {"question": question, "answer": answer}

    cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def generate_match_report(fixture_id: int, force_refresh: bool = False, lang: str = "fr") -> dict:
    """Génère (ou relit depuis le cache) le rapport complet d'un match.

    3 appels LLM au total, quel que soit le nombre de joueurs du match.
    Le rapport est mis en cache par langue (fr/en).
    """
    cache_file = _report_cache_path(fixture_id, lang)
    if cache_file.exists() and not force_refresh:
        report = json.loads(cache_file.read_text(encoding="utf-8"))
        # Les faits marquants sont déterministes : on les (re)calcule à la lecture
        # pour que même un ancien rapport caché les expose (sans régénérer le LLM).
        report.setdefault("insights", match_insights(rank_players(fixture_id)))
        return report

    ranked_players = rank_players(fixture_id)
    if not ranked_players:
        raise ValueError(f"Aucun joueur trouvé pour le fixture {fixture_id}.")

    raw = fetch_fixture(fixture_id)
    events_summary = _summarize_events(raw.get("events"))
    insights = match_insights(ranked_players)

    motm = ranked_players[0]
    motm_report = generate_report(
        motm_report_prompt(motm, ranked_players, events_summary, insights=insights), lang=lang
    )

    enriched_players = []
    for player in ranked_players:
        enriched = dict(player)
        recent_matches = _recent_form(player["player_id"], exclude_fixture_id=fixture_id)
        if recent_matches:
            enriched["recent_matches"] = recent_matches
        player_events = _events_for_player(events_summary, player["player_id"])
        if player_events:
            enriched["match_events"] = player_events
        enriched_players.append(enriched)

    player_ids = [str(p["player_id"]) for p in ranked_players]
    batch_text = generate_report(batch_player_analysis_prompt(enriched_players), lang=lang)
    player_reports = _parse_batch_blocks(
        batch_text, player_ids, fallback="Analyse indisponible pour ce joueur."
    )

    teams: dict[str, list[dict]] = {}
    for player in ranked_players:
        teams.setdefault(player["team_name"], []).append(player)
    team_names = list(teams.keys())

    tactics_text = generate_report(batch_tactical_suggestions_prompt(teams), lang=lang)
    tactics_by_index = _parse_batch_blocks(
        tactics_text,
        [str(i) for i in range(1, len(team_names) + 1)],
        fallback="Suggestions tactiques indisponibles.",
    )
    tactical_suggestions = {
        team_name: tactics_by_index[str(idx)]
        for idx, team_name in enumerate(team_names, start=1)
    }

    report = {
        "fixture_id": fixture_id,
        "motm_player_id": motm["player_id"],
        "motm_report": motm_report,
        "player_reports": player_reports,
        "tactical_suggestions": tactical_suggestions,
        "insights": insights,
    }

    cache_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
