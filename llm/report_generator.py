"""Orchestration : scores ML -> prompts -> LLM -> rapport structuré.

Les rapports générés sont mis en cache sur disque (data/processed/) pour
éviter de regénérer un rapport à chaque appel API et donc de gaspiller des
tokens LLM.

Le rapport complet (tous les joueurs + tactique) est généré via 3 appels LLM
batchés (1 MOTM + 1 pour tous les joueurs + 1 pour les deux équipes) plutôt
qu'un appel par joueur/équipe : sur un match à 30 joueurs ça remplace ~33
appels séquentiels par 3, ce qui évite de saturer les limites de requêtes/
minute des plans LLM gratuits.
"""
import json
import re
from pathlib import Path

from config import DATA_PROCESSED_DIR
from llm.llm_client import generate_report
from llm.prompt_templates import (
    batch_player_analysis_prompt,
    batch_tactical_suggestions_prompt,
    motm_report_prompt,
    player_analysis_prompt,
)
from ml.scoring_engine import rank_players


def _report_cache_path(fixture_id: int) -> Path:
    return DATA_PROCESSED_DIR / f"{fixture_id}_report.json"


def _player_analysis_cache_path(fixture_id: int, player_id: int) -> Path:
    return DATA_PROCESSED_DIR / f"{fixture_id}_player_{player_id}.json"


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


def get_player_analysis(fixture_id: int, player_id: int, force_refresh: bool = False) -> dict:
    """Retourne le score ML + l'analyse LLM d'un joueur, avec mise en cache."""
    ranked_players = rank_players(fixture_id)
    player = next((p for p in ranked_players if p["player_id"] == player_id), None)
    if player is None:
        raise ValueError(f"Joueur {player_id} introuvable pour le fixture {fixture_id}.")

    cache_file = _player_analysis_cache_path(fixture_id, player_id)
    if cache_file.exists() and not force_refresh:
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        cached["score"] = player
        return cached

    analysis = generate_report(player_analysis_prompt(player))
    result = {"score": player, "analysis": analysis}

    cache_file.write_text(
        json.dumps({"analysis": analysis}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def generate_match_report(fixture_id: int, force_refresh: bool = False) -> dict:
    """Génère (ou relit depuis le cache) le rapport complet d'un match.

    3 appels LLM au total, quel que soit le nombre de joueurs du match.
    """
    cache_file = _report_cache_path(fixture_id)
    if cache_file.exists() and not force_refresh:
        return json.loads(cache_file.read_text(encoding="utf-8"))

    ranked_players = rank_players(fixture_id)
    if not ranked_players:
        raise ValueError(f"Aucun joueur trouvé pour le fixture {fixture_id}.")

    motm = ranked_players[0]
    motm_report = generate_report(motm_report_prompt(motm, ranked_players))

    player_ids = [str(p["player_id"]) for p in ranked_players]
    batch_text = generate_report(batch_player_analysis_prompt(ranked_players))
    player_reports = _parse_batch_blocks(
        batch_text, player_ids, fallback="Analyse indisponible pour ce joueur."
    )

    teams: dict[str, list[dict]] = {}
    for player in ranked_players:
        teams.setdefault(player["team_name"], []).append(player)
    team_names = list(teams.keys())

    tactics_text = generate_report(batch_tactical_suggestions_prompt(teams))
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
    }

    cache_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
