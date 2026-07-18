"""Templates de prompts pour la génération de rapports par le LLM.

Règle stricte : le LLM ne calcule jamais de statistique. Il reçoit toujours
un JSON de données déjà calculées par ml/scoring_engine.py et se contente
de l'interpréter en langage naturel.
"""
import json

SYSTEM_PROMPT = (
    "Tu es un analyste tactique de football qui rédige des rapports de match. "
    "Tu ne dois jamais inventer ou modifier une statistique. Utilise uniquement "
    "les chiffres fournis dans le JSON ci-dessous. Ton rôle est d'interpréter, "
    "pas de calculer. Réponds en français, dans un style journalistique concis."
)


def _to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def motm_report_prompt(motm: dict, all_players: list[dict]) -> str:
    ranking_summary = [
        {"name": p["name"], "position": p["position"], "composite_score": p["composite_score"]}
        for p in all_players[:5]
    ]
    return (
        "Voici le joueur désigné Homme du Match (MOTM) et le top 5 du classement "
        "du match, calculés par le moteur de scoring :\n\n"
        f"MOTM:\n{_to_json(motm)}\n\n"
        f"Top 5 du match:\n{_to_json(ranking_summary)}\n\n"
        "Rédige un rapport de 3 à 5 phrases expliquant pourquoi ce joueur a obtenu "
        "le meilleur score composite, en t'appuyant uniquement sur le breakdown et "
        "les points forts fournis."
    )


def player_analysis_prompt(player: dict) -> str:
    return (
        "Voici les données calculées pour un joueur de ce match :\n\n"
        f"{_to_json(player)}\n\n"
        "Transforme ce breakdown en une analyse de 2 à 4 phrases : explique ses "
        "points forts et points faibles en langage naturel et compréhensible, "
        "sans jamais introduire de nouveau chiffre."
    )


def tactical_suggestions_prompt(team_name: str, team_players: list[dict]) -> str:
    weaknesses_summary = [
        {"name": p["name"], "position": p["position"], "weaknesses": p["weaknesses"]}
        for p in team_players
    ]
    return (
        f"Voici les points faibles individuels détectés pour les joueurs de "
        f"l'équipe {team_name} lors de ce match :\n\n"
        f"{_to_json(weaknesses_summary)}\n\n"
        "En te basant uniquement sur les faiblesses collectives récurrentes "
        "(ex : plusieurs joueurs faibles sur le même type d'action), propose "
        "2 à 3 ajustements tactiques concrets pour le prochain match. Ne cite "
        "aucune statistique qui ne figure pas ci-dessus."
    )


BLOCK_DELIMITER_TEMPLATE = "[[{key}]]"


def batch_player_analysis_prompt(players: list[dict]) -> str:
    """Un seul prompt pour TOUS les joueurs du match (au lieu d'un appel par joueur).

    Réduit un rapport de ~30 appels LLM séquentiels à un seul appel, ce qui
    évite de saturer le quota du plan gratuit (souvent quelques dizaines de
    requêtes/minute). Le format de sortie ([[player_id]] ... ) est parsé par
    llm/report_generator.py::_parse_batch_blocks.
    """
    slim_players = [
        {k: v for k, v in p.items() if k not in ("radar",)} for p in players
    ]
    example = BLOCK_DELIMITER_TEMPLATE.format(key=players[0]["player_id"]) if players else "[[123]]"
    return (
        "Voici les données calculées (moteur ML) pour TOUS les joueurs de ce match :\n\n"
        f"{_to_json(slim_players)}\n\n"
        "Pour CHAQUE joueur de la liste, rédige une analyse de 2 à 4 phrases "
        "(points forts/faibles en langage naturel, sans jamais introduire de "
        "nouveau chiffre). Réponds STRICTEMENT selon ce format, un bloc par "
        "joueur, sans aucun texte avant/après/entre les blocs :\n\n"
        f"{example}\n<analyse de ce joueur>\n\n"
        "Répète ce bloc pour CHAQUE player_id de la liste fournie, dans le même ordre, "
        "en remplaçant l'ID entre crochets doubles par le player_id exact du joueur concerné."
    )


def batch_tactical_suggestions_prompt(teams: dict[str, list[dict]]) -> str:
    """Un seul prompt pour LES DEUX équipes (au lieu d'un appel par équipe)."""
    sections = []
    for idx, (team_name, players) in enumerate(teams.items(), start=1):
        weaknesses_summary = [
            {"name": p["name"], "position": p["position"], "weaknesses": p["weaknesses"]}
            for p in players
        ]
        sections.append(f"Équipe {idx} ({team_name}) :\n{_to_json(weaknesses_summary)}")

    return (
        "Voici les points faibles individuels détectés pour les joueurs des "
        "deux équipes de ce match :\n\n" + "\n\n".join(sections) + "\n\n"
        "Pour CHAQUE équipe, en te basant uniquement sur les faiblesses "
        "collectives récurrentes (ex : plusieurs joueurs faibles sur le même "
        "type d'action), propose 2 à 3 ajustements tactiques concrets. Ne cite "
        "aucune statistique qui ne figure pas ci-dessus. Réponds STRICTEMENT "
        "selon ce format, sans texte avant/après/entre les blocs :\n\n"
        "[[1]]\n<suggestions équipe 1>\n\n[[2]]\n<suggestions équipe 2>"
    )
