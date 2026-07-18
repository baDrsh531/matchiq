"""Pondération des statistiques par poste pour le moteur de scoring.

Chaque catégorie de stat a :
- un poids par poste (le signe indique si la stat est bénéfique ou pénalisante)
- une configuration de normalisation (STAT_CONFIG) commune à tous les postes,
  qui ramène la stat brute à une échelle 0-1 (rate) avant pondération.
"""

# poids par poste : la somme des poids positifs avoisine 1.0 pour chaque poste,
# ce qui permet de combiner les contributions avant normalisation finale 0-10.
POSITION_WEIGHTS = {
    "Goalkeeper": {
        "saves": 0.35,
        "goals_conceded": -0.30,
        "passes_accuracy": 0.10,
        "duels_won": 0.05,
        "penalty_saved": 0.15,
        "cards_yellow": -0.05,
        "cards_red": -0.20,
    },
    "Defender": {
        "tackles": 0.20,
        "interceptions": 0.20,
        "duels_won": 0.15,
        "passes_accuracy": 0.15,
        "goals": 0.10,
        "blocks": 0.10,
        "fouls_committed": -0.10,
        "cards_yellow": -0.05,
        "cards_red": -0.20,
    },
    "Midfielder": {
        "passes_key": 0.20,
        "passes_accuracy": 0.15,
        "dribbles_success": 0.15,
        "tackles": 0.10,
        "goals": 0.15,
        "assists": 0.15,
        "interceptions": 0.10,
        "fouls_committed": -0.05,
        "cards_yellow": -0.05,
        "cards_red": -0.20,
    },
    "Attacker": {
        "goals": 0.30,
        "shots_on_target": 0.15,
        "assists": 0.20,
        "dribbles_success": 0.15,
        "duels_won": 0.10,
        "passes_key": 0.10,
        "fouls_committed": -0.05,
        "cards_yellow": -0.05,
        "cards_red": -0.20,
    },
}

# valeur de référence "excellente performance" utilisée pour ramener une stat
# brute sur une échelle 0-1 (1.3 max après clip, pour ne pas plafonner trop tôt).
# les stats en pourcentage (passes_accuracy) sont gérées séparément (is_rate=True).
STAT_CONFIG = {
    "saves": {"ref_max": 6, "is_rate": False},
    "goals_conceded": {"ref_max": 4, "is_rate": False},
    "passes_accuracy": {"ref_max": 100, "is_rate": True},
    "duels_won": {"ref_max": 10, "is_rate": False},
    "penalty_saved": {"ref_max": 1, "is_rate": False},
    "tackles": {"ref_max": 6, "is_rate": False},
    "interceptions": {"ref_max": 5, "is_rate": False},
    "goals": {"ref_max": 2, "is_rate": False},
    "blocks": {"ref_max": 4, "is_rate": False},
    "fouls_committed": {"ref_max": 4, "is_rate": False},
    "passes_key": {"ref_max": 5, "is_rate": False},
    "dribbles_success": {"ref_max": 6, "is_rate": False},
    "assists": {"ref_max": 2, "is_rate": False},
    "shots_on_target": {"ref_max": 5, "is_rate": False},
    "cards_yellow": {"ref_max": 1, "is_rate": False},
    "cards_red": {"ref_max": 1, "is_rate": False},
}

# libellés lisibles pour les rapports LLM et le frontend
CATEGORY_LABELS = {
    "saves": "arrêts",
    "goals_conceded": "buts encaissés",
    "passes_accuracy": "précision des passes",
    "duels_won": "duels gagnés",
    "penalty_saved": "penalty arrêté",
    "tackles": "tacles",
    "interceptions": "interceptions",
    "goals": "buts",
    "blocks": "contres",
    "fouls_committed": "fautes commises",
    "passes_key": "passes clés",
    "dribbles_success": "dribbles réussis",
    "assists": "passes décisives",
    "shots_on_target": "tirs cadrés",
    "cards_yellow": "cartons jaunes",
    "cards_red": "cartons rouges",
}
