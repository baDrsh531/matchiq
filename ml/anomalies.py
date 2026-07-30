"""Détection d'écarts de performance : repère les matchs où un joueur sort
nettement de son propre standard.

Approche assumée et honnête : pas de « détection d'anomalies » exotique, mais un
z-score classique — l'écart d'un match à la moyenne du joueur, mesuré en nombre
d'écarts-types de son historique. Un |z| élevé signale un match statistiquement
inhabituel POUR CE JOUEUR (record personnel ou contre-performance), pas dans
l'absolu. Il faut donc un minimum de matchs pour que la baseline ait un sens.

Le moteur reste déterministe : mêmes matchs en entrée → mêmes alertes en sortie,
aucun appel modèle. Un LLM pourra commenter l'alerte, il ne la produit jamais.
"""
from __future__ import annotations

from typing import Optional

MIN_MATCHES = 3          # en-deçà, la baseline personnelle n'est pas fiable
Z_THRESHOLD = 1.5        # au-delà (en valeur absolue), le match est signalé


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n     # écart-type population
    return mean, var ** 0.5


def detect_anomalies(matches: list[dict], min_matches: int = MIN_MATCHES,
                     z_threshold: float = Z_THRESHOLD) -> dict:
    """Analyse l'historique d'un joueur (liste de matchs avec ``composite_score``)
    et renvoie ses écarts marquants.

    Retour :
      {
        "enough_data": bool,          # False si trop peu de matchs pour conclure
        "baseline": {"mean", "std", "n"},
        "anomalies": [ {fixture_id, opponent_name, date, composite_score,
                        z, type, delta} ],   # type: "record" | "contre-performance"
        "latest_alert": {...} | None, # le DERNIER match s'il est lui-même une anomalie
      }
    """
    scored = [m for m in matches if m.get("composite_score") is not None]
    n = len(scored)
    if n < min_matches:
        return {"enough_data": False, "baseline": {"mean": None, "std": None, "n": n},
                "anomalies": [], "latest_alert": None}

    values = [float(m["composite_score"]) for m in scored]
    mean, std = _mean_std(values)
    baseline = {"mean": round(mean, 2), "std": round(std, 2), "n": n}

    if std == 0:  # joueur parfaitement régulier : aucun écart à signaler
        return {"enough_data": True, "baseline": baseline, "anomalies": [], "latest_alert": None}

    anomalies = []
    for m in scored:
        score = float(m["composite_score"])
        z = (score - mean) / std
        if abs(z) >= z_threshold:
            anomalies.append({
                "fixture_id": m.get("fixture_id"),
                "opponent_name": m.get("opponent_name"),
                "date": m.get("date"),
                "composite_score": round(score, 2),
                "z": round(z, 2),
                "type": "record" if z > 0 else "contre-performance",
                "delta": round(score - mean, 2),
            })

    # « Alerte » façon monitoring : le dernier match joué est-il lui-même hors norme ?
    latest = scored[-1]
    latest_alert = next(
        (a for a in anomalies if a["fixture_id"] == latest.get("fixture_id")), None
    )
    # Tri des anomalies par ampleur décroissante (plus parlant à l'affichage).
    anomalies.sort(key=lambda a: -abs(a["z"]))
    return {"enough_data": True, "baseline": baseline,
            "anomalies": anomalies, "latest_alert": latest_alert}
