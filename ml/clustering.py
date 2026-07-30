"""Classement non supervisé des équipes par style de jeu (k-means, numpy pur).

À partir des statistiques collectives d'un match (possession, tirs, passes,
corners, fautes...), on résume chaque équipe par un vecteur de style moyen, on
standardise, puis on regroupe les équipes en `k` familles avec un k-means maison.

Deux choix pour rester honnête et reproductible :
  * pas de sklearn — un k-means de ~30 lignes suffit et montre l'algorithme ;
  * initialisation DÉTERMINISTE (k points les plus écartés, façon k-means++ sans
    aléa) : mêmes équipes en entrée -> mêmes clusters en sortie, à chaque appel.

Chaque cluster est ensuite étiqueté par l'axe où son centre se démarque le plus
(ex. « possession », « volume de tirs »), plutôt que par une étiquette plaquée
d'avance — la description sort des données, elle n'y est pas imposée.
"""
from __future__ import annotations

import numpy as np

# Axes de style extraits des statistiques API-Football, avec un libellé lisible.
STYLE_FEATURES = {
    "Ball Possession": "possession",
    "Total Shots": "volume de tirs",
    "Shots on Goal": "tirs cadrés",
    "Corner Kicks": "jeu par les côtés",
    "Fouls": "engagement/fautes",
    "Passes accurate": "précision de passe",
    "Passes %": "précision de passe",
    "offsides": "jeu en profondeur",
}


def _to_number(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, str):
        value = value.replace("%", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def extract_team_features(fixtures: list[dict]) -> list[dict]:
    """Agrège un vecteur de style moyen par équipe à partir de fixtures bruts
    (clé ``statistics`` d'un fetch_fixture). Renvoie une liste
    ``[{team_id, name, matches, features:{axe: valeur}}]``."""
    acc: dict[int, dict] = {}
    for raw in fixtures:
        for team_stats in raw.get("statistics", []) or []:
            team = team_stats.get("team", {})
            tid = team.get("id")
            if tid is None:
                continue
            entry = acc.setdefault(tid, {"team_id": tid, "name": team.get("name"),
                                         "matches": 0, "sums": {}})
            entry["name"] = team.get("name") or entry["name"]
            entry["matches"] += 1
            for stat in team_stats.get("statistics", []) or []:
                label = STYLE_FEATURES.get(stat.get("type"))
                if label:
                    entry["sums"][label] = entry["sums"].get(label, 0.0) + _to_number(stat.get("value"))
    out = []
    for e in acc.values():
        n = max(1, e["matches"])
        out.append({"team_id": e["team_id"], "name": e["name"], "matches": e["matches"],
                    "features": {k: v / n for k, v in e["sums"].items()}})
    return out


def _standardize(matrix: np.ndarray) -> np.ndarray:
    mean, std = matrix.mean(axis=0), matrix.std(axis=0)
    std_safe = np.where(std == 0, 1.0, std)
    z = (matrix - mean) / std_safe
    z[:, std == 0] = 0.0
    return z


def _init_centroids(z: np.ndarray, k: int) -> np.ndarray:
    """Init déterministe type k-means++ sans aléa : 1er centre = point le plus
    éloigné du barycentre, puis on ajoute à chaque fois le point le plus loin des
    centres déjà choisis."""
    centroids = [int(np.argmax(np.linalg.norm(z - z.mean(axis=0), axis=1)))]
    while len(centroids) < k:
        dist = np.min(
            [np.linalg.norm(z - z[c], axis=1) for c in centroids], axis=0
        )
        centroids.append(int(np.argmax(dist)))
    return z[centroids].copy()


def kmeans(z: np.ndarray, k: int, iters: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """k-means déterministe. Renvoie (labels, centroids)."""
    centroids = _init_centroids(z, k)
    labels = np.zeros(len(z), dtype=int)
    for _ in range(iters):
        dists = np.stack([np.linalg.norm(z - c, axis=1) for c in centroids], axis=1)
        new_labels = dists.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for c in range(k):
            members = z[labels == c]
            if len(members):
                centroids[c] = members.mean(axis=0)
    return labels, centroids


def cluster_teams(teams: list[dict], k: int = 3) -> dict:
    """Regroupe des équipes par style. `teams` = sortie d'extract_team_features.

    Renvoie ``{'clusters': [{label, teams:[...]}], 'features': [...]}`` ou, si
    trop peu d'équipes pour former `k` groupes, ``{'enough_data': False, ...}``.
    """
    if len(teams) < max(k, 2) or k < 1:
        return {"enough_data": False, "reason": "trop peu d'équipes pour un clustering fiable",
                "n_teams": len(teams), "clusters": []}

    features = sorted({f for t in teams for f in t["features"]})
    matrix = np.array([[t["features"].get(f, 0.0) for f in features] for t in teams], dtype=float)
    z = _standardize(matrix)
    labels, centroids = kmeans(z, k)

    clusters = []
    for c in range(k):
        members = [teams[i] for i in range(len(teams)) if labels[i] == c]
        if not members:
            continue
        # Étiquette : l'axe où le centre du cluster s'écarte le plus de la moyenne.
        centroid = centroids[c]
        dominant_idx = int(np.argmax(np.abs(centroid)))
        direction = "élevé" if centroid[dominant_idx] > 0 else "faible"
        clusters.append({
            "label": f"{features[dominant_idx]} ({direction})",
            "dominant_feature": features[dominant_idx],
            "teams": [{"team_id": m["team_id"], "name": m["name"]} for m in members],
        })
    return {"enough_data": True, "n_teams": len(teams), "features": features, "clusters": clusters}
