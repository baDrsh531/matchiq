"""Recherche de joueurs au profil statistique proche.

Nommage honnête : ce ne sont pas des « embeddings » neuronaux, mais une
similarité cosinus sur des vecteurs de statistiques. Chaque joueur est déjà
décrit par son `breakdown` (contributions pondérées par catégorie). On :

  1. ne compare que des joueurs du MÊME POSTE (leurs catégories sont alignées —
     un gardien et un ailier n'ont pas les mêmes axes) ;
  2. standardise chaque catégorie sur l'ensemble du poste (z-score), pour qu'une
     stat à grande échelle ne domine pas mécaniquement la mesure ;
  3. classe les autres joueurs par similarité cosinus décroissante.

Après standardisation, la cosinus compare des PROFILS RELATIFS : deux joueurs
proches sont forts/faibles sur les mêmes axes par rapport à la moyenne du poste,
indépendamment de leur niveau absolu.

Déterministe et sans dépendance lourde (numpy seul).
"""
from __future__ import annotations

import numpy as np


def _feature_matrix(profiles: list[dict]) -> tuple[np.ndarray, list[str]]:
    """Construit la matrice (joueurs × catégories) à partir des breakdown, sur
    l'union ordonnée des catégories (catégorie absente d'un joueur -> 0)."""
    keys: list[str] = []
    for p in profiles:
        for k in p.get("breakdown", {}):
            if k not in keys:
                keys.append(k)
    matrix = np.array(
        [[float(p.get("breakdown", {}).get(k, 0.0)) for k in keys] for p in profiles],
        dtype=float,
    )
    return matrix, keys


def _standardize(matrix: np.ndarray) -> np.ndarray:
    """Centre-réduit chaque colonne (z-score). Colonnes de variance nulle -> 0."""
    mean = matrix.mean(axis=0)
    std = matrix.std(axis=0)
    std_safe = np.where(std == 0, 1.0, std)
    z = (matrix - mean) / std_safe
    z[:, std == 0] = 0.0
    return z


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def similar_players(target_id: int, profiles: list[dict], limit: int = 5) -> list[dict]:
    """Renvoie les `limit` joueurs les plus proches de `target_id` par style.

    `profiles` doit contenir des joueurs d'UN SEUL poste (celui de la cible) —
    typiquement le retour de ``repository.player_profiles(session, position)``.
    Chaque résultat porte un champ ``similarity`` dans [-1, 1] (1 = profil quasi
    identique)."""
    idx = next((i for i, p in enumerate(profiles) if p["player_id"] == target_id), None)
    if idx is None or len(profiles) < 2:
        return []

    matrix, _keys = _feature_matrix(profiles)
    z = _standardize(matrix)
    target_vec = z[idx]

    scored = []
    for i, p in enumerate(profiles):
        if i == idx:
            continue
        scored.append({
            "player_id": p["player_id"],
            "name": p["name"],
            "photo_url": p.get("photo_url"),
            "team_id": p.get("team_id"),
            "team_name": p.get("team_name"),
            "position": p.get("position"),
            "average_score": p.get("average_score"),
            "appearances": p.get("appearances"),
            "similarity": round(_cosine(target_vec, z[i]), 3),
        })
    scored.sort(key=lambda s: -s["similarity"])
    return scored[:limit]
