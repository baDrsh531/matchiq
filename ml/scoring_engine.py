"""Moteur de scoring composite par joueur (inspiré VAEP).

Chaque action d'un joueur est résumée par les stats fournies par l'API-Football,
converties en contribution pondérée selon son poste (ml/position_weights.py),
puis normalisées sur une échelle 0-10 comparable entre postes.

Les points forts/faibles sont détectés en comparant la contribution de chaque
catégorie à la moyenne/écart-type des joueurs du même poste dans le match.
"""
from typing import Any, Optional

import numpy as np

from ml.ingestion import fetch_fixture
from ml.position_weights import CATEGORY_LABELS, POSITION_WEIGHTS, STAT_CONFIG
from ml.schemas import POSITION_CODE_MAP, PlayerMatchStats

Z_SCORE_THRESHOLD = 1.0


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    return int(_to_float(value))


def extract_player_stats(raw_fixture: dict) -> list[PlayerMatchStats]:
    """Parse la réponse combinée d'ingestion.fetch_fixture en liste de PlayerMatchStats."""
    players_payload = raw_fixture.get("players") or []
    result: list[PlayerMatchStats] = []

    for team_block in players_payload:
        team = team_block.get("team") or {}
        team_id = team.get("id")
        team_name = team.get("name", "")
        team_logo = team.get("logo")

        for entry in team_block.get("players") or []:
            player = entry.get("player") or {}
            stats_list = entry.get("statistics") or [{}]
            s = stats_list[0] if stats_list else {}

            games = s.get("games") or {}
            position_code = games.get("position") or "M"
            position = POSITION_CODE_MAP.get(position_code, "Midfielder")

            shots = s.get("shots") or {}
            goals = s.get("goals") or {}
            passes = s.get("passes") or {}
            tackles = s.get("tackles") or {}
            duels = s.get("duels") or {}
            dribbles = s.get("dribbles") or {}
            fouls = s.get("fouls") or {}
            cards = s.get("cards") or {}
            penalty = s.get("penalty") or {}

            result.append(
                PlayerMatchStats(
                    player_id=player.get("id", 0),
                    name=player.get("name", "Inconnu"),
                    photo_url=player.get("photo"),
                    team_id=team_id,
                    team_name=team_name,
                    team_logo=team_logo,
                    position=position,
                    minutes=_to_int(games.get("minutes")),
                    rating=_to_float(games.get("rating")) or None,
                    captain=bool(games.get("captain")),
                    substitute=bool(games.get("substitute")),
                    shots_total=_to_int(shots.get("total")),
                    shots_on_target=_to_int(shots.get("on")),
                    goals=_to_int(goals.get("total")),
                    goals_conceded=_to_int(goals.get("conceded")),
                    assists=_to_int(goals.get("assists")),
                    saves=_to_int(goals.get("saves")),
                    passes_total=_to_int(passes.get("total")),
                    passes_key=_to_int(passes.get("key")),
                    passes_accuracy=_to_float(passes.get("accuracy")),
                    tackles=_to_int(tackles.get("total")),
                    blocks=_to_int(tackles.get("blocks")),
                    interceptions=_to_int(tackles.get("interceptions")),
                    duels_total=_to_int(duels.get("total")),
                    duels_won=_to_int(duels.get("won")),
                    dribbles_attempts=_to_int(dribbles.get("attempts")),
                    dribbles_success=_to_int(dribbles.get("success")),
                    fouls_drawn=_to_int(fouls.get("drawn")),
                    fouls_committed=_to_int(fouls.get("committed")),
                    cards_yellow=_to_int(cards.get("yellow")),
                    cards_red=_to_int(cards.get("red")),
                    penalty_scored=_to_int(penalty.get("scored")),
                    penalty_missed=_to_int(penalty.get("missed")),
                    penalty_saved=_to_int(penalty.get("saved")),
                )
            )

    return result


def _normalize_value(raw_value: float, category: str) -> float:
    cfg = STAT_CONFIG[category]
    if raw_value <= 0:
        return 0.0
    return min(raw_value / cfg["ref_max"], 1.3)


def _category_values(stats: PlayerMatchStats, position: str) -> dict[str, float]:
    weights = POSITION_WEIGHTS.get(position, POSITION_WEIGHTS["Midfielder"])
    raw_map = stats.model_dump()
    return {cat: _normalize_value(float(raw_map.get(cat, 0) or 0), cat) for cat in weights}


def _detect_strengths_weaknesses(
    breakdown: dict[str, float],
    population_stats: Optional[dict[str, tuple[float, float]]],
) -> tuple[list[str], list[str]]:
    if not population_stats:
        ranked = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
        strengths = [CATEGORY_LABELS.get(c, c) for c, v in ranked[:2]]
        weaknesses = [CATEGORY_LABELS.get(c, c) for c, v in ranked[-2:]]
        return strengths, weaknesses

    z_scores: dict[str, float] = {}
    for category, value in breakdown.items():
        mean, std = population_stats.get(category, (0.0, 0.0))
        z_scores[category] = (value - mean) / std if std > 1e-6 else 0.0

    ranked = sorted(z_scores.items(), key=lambda kv: kv[1], reverse=True)

    strengths = [CATEGORY_LABELS.get(c, c) for c, z in ranked if z >= Z_SCORE_THRESHOLD][:3]
    weaknesses = [CATEGORY_LABELS.get(c, c) for c, z in ranked if z <= -Z_SCORE_THRESHOLD][-3:]

    if not strengths:
        strengths = [CATEGORY_LABELS.get(c, c) for c, _ in ranked[:2]]
    if not weaknesses:
        weaknesses = [CATEGORY_LABELS.get(c, c) for c, _ in ranked[-2:]]

    return strengths, weaknesses


def compute_player_score(
    player_stats: PlayerMatchStats,
    position: str,
    population_stats: Optional[dict[str, tuple[float, float]]] = None,
) -> dict:
    """Calcule la contribution pondérée d'un joueur pour son poste.

    Retourne un dict avec `raw_score` (contribution brute, à normaliser 0-10
    au niveau du match complet par rank_players) et le détail par catégorie.
    """
    weights = POSITION_WEIGHTS.get(position, POSITION_WEIGHTS["Midfielder"])
    normalized_values = _category_values(player_stats, position)
    breakdown = {cat: round(weights[cat] * normalized_values[cat], 4) for cat in weights}
    raw_score = sum(breakdown.values())

    strengths, weaknesses = _detect_strengths_weaknesses(breakdown, population_stats)
    radar = {
        CATEGORY_LABELS.get(cat, cat): round(value * 10, 1)
        for cat, value in normalized_values.items()
    }

    return {
        "player_id": player_stats.player_id,
        "name": player_stats.name,
        "photo_url": player_stats.photo_url,
        "team_id": player_stats.team_id,
        "team_name": player_stats.team_name,
        "team_logo": player_stats.team_logo,
        "position": position,
        "minutes": player_stats.minutes,
        "raw_score": raw_score,
        "breakdown": breakdown,
        "radar": radar,
        "strengths": strengths,
        "weaknesses": weaknesses,
    }


def rank_players(fixture_id: int) -> list[dict]:
    """Calcule et classe tous les joueurs d'un match par score composite 0-10.

    Le premier élément de la liste retournée est le Homme du Match (MOTM).
    """
    raw = fetch_fixture(fixture_id)
    all_stats = extract_player_stats(raw)
    played = [s for s in all_stats if s.minutes > 0]

    if not played:
        return []

    first_pass = [compute_player_score(s, s.position) for s in played]

    population_stats: dict[str, dict[str, tuple[float, float]]] = {}
    for position, weights in POSITION_WEIGHTS.items():
        peers = [p for p in first_pass if p["position"] == position]
        if not peers:
            continue
        stats_per_cat: dict[str, tuple[float, float]] = {}
        for cat in weights:
            values = np.array([p["breakdown"][cat] for p in peers], dtype=float)
            stats_per_cat[cat] = (float(values.mean()), float(values.std()))
        population_stats[position] = stats_per_cat

    final_scores = [
        compute_player_score(s, s.position, population_stats.get(s.position)) for s in played
    ]

    raw_values = [p["raw_score"] for p in final_scores]
    lo, hi = min(raw_values), max(raw_values)
    for p in final_scores:
        if hi - lo < 1e-6:
            p["composite_score"] = 5.0
        else:
            p["composite_score"] = round(10 * (p["raw_score"] - lo) / (hi - lo), 2)
        del p["raw_score"]

    final_scores.sort(key=lambda p: p["composite_score"], reverse=True)
    return final_scores


def get_man_of_the_match(fixture_id: int) -> dict:
    ranked = rank_players(fixture_id)
    if not ranked:
        raise ValueError("Aucun joueur avec du temps de jeu trouvé pour ce fixture.")
    return ranked[0]
