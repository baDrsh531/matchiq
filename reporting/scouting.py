"""Assemblage des données d'une fiche de scouting joueur (orientée recrutement).

Tout est déterministe et agrégé depuis la base : profil moyen du joueur, comparé
à la moyenne de son poste (les autres joueurs analysés au même poste), points
forts/faibles qui en découlent, joueurs au style proche et écarts de performance.
Le « résumé exécutif » est une phrase construite par règles — aucun LLM, aucun
chiffre inventé. La mise en page PDF vit dans reporting/pdf_report.py.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ml.anomalies import detect_anomalies
from ml.similarity import similar_players
from persistence.repository import get_player_history, player_profiles

# Catégories de contribution où « plus haut = mieux » ne tient pas : on les
# exclut de la lecture forces/faiblesses (un carton n'est pas une force).
_NEGATIVE_KEYS = {"cards_yellow", "cards_red", "fouls_committed", "goals_conceded"}


def _baseline(profiles: list[dict], exclude_id: int) -> dict:
    """Moyenne par catégorie sur tous les joueurs du poste (hors le joueur ciblé)."""
    others = [p for p in profiles if p["player_id"] != exclude_id]
    sums: dict[str, float] = {}
    for p in others:
        for k, v in p["breakdown"].items():
            sums[k] = sums.get(k, 0.0) + v
    n = max(1, len(others))
    return {k: v / n for k, v in sums.items()}, len(others)


def build_scouting_data(session: Session, player_id: int) -> dict | None:
    """Rassemble toutes les données d'une fiche scouting, ou None si le joueur est
    absent de l'historique."""
    history = get_player_history(session, player_id)
    if history is None:
        return None

    position = history["position"]
    pool = player_profiles(session, position)
    target = next((p for p in pool if p["player_id"] == player_id), None)
    features = target["breakdown"] if target else {}
    baseline, baseline_n = _baseline(pool, player_id)

    # Forces / faiblesses = plus gros écarts (signés) à la moyenne du poste, en
    # ignorant les catégories « négatives » (cartons, fautes...).
    deltas = []
    for k, v in features.items():
        if k in _NEGATIVE_KEYS:
            continue
        deltas.append((k, v - baseline.get(k, 0.0)))
    deltas.sort(key=lambda kv: kv[1])
    strengths = [k for k, d in reversed(deltas) if d > 0][:3]
    weaknesses = [k for k, d in deltas if d < 0][:3]

    avg = history["average_score"]
    pool_avg = (sum(p["average_score"] for p in pool) / len(pool)) if pool else avg
    stance = "au-dessus de" if avg >= pool_avg else "en dessous de"
    exec_summary = (
        f"{history['name']} affiche une note moyenne de {avg:.1f}/10 sur "
        f"{history['matches_played']} match(s), {stance} la moyenne des "
        f"{position.lower()}s analysés ({pool_avg:.1f}). "
        + (f"Points forts : {', '.join(strengths)}. " if strengths else "")
        + (f"À surveiller : {', '.join(weaknesses)}." if weaknesses else "")
    ).strip()

    return {
        "player": {
            "player_id": player_id, "name": history["name"], "team_name": history["team_name"],
            "position": position, "average_score": avg,
            "matches_played": history["matches_played"], "pool_average": round(pool_avg, 2),
        },
        "exec_summary": exec_summary,
        "features": features,
        "baseline": baseline,
        "baseline_n": baseline_n,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "similar": similar_players(player_id, pool, limit=3),
        "anomalies": detect_anomalies(history["matches"]),
    }
