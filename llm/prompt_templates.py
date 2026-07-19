"""Templates de prompts pour la génération de rapports par le LLM.

Règle stricte : le LLM ne calcule jamais de statistique. Il reçoit toujours
un JSON de données déjà calculées par ml/scoring_engine.py et se contente
de l'interpréter en langage naturel — mais "interpréter" veut dire expliquer
la portée tactique des chiffres (et les relier au déroulé du match / à la
forme récente du joueur quand ces informations sont fournies), pas les
réciter.
"""
import json

SYSTEM_PROMPT = (
    "Tu es un analyste tactique professionnel qui commente des matchs de "
    "football pour un public averti. Tu ne dois JAMAIS inventer ou modifier "
    "une statistique : utilise uniquement les chiffres fournis dans le JSON. "
    "Mais ton travail n'est PAS de réciter ces chiffres — c'est de les "
    "interpréter comme le ferait un vrai analyste : explique ce qu'ils "
    "signifient tactiquement, relie-les au déroulé du match (buts, cartons, "
    "changements) ou à la forme récente du joueur quand ces informations "
    "sont fournies, et formule des constats concrets plutôt que des "
    "généralités. Évite les tournures du type 'il obtient un score de X dans "
    "la catégorie Y' — dis plutôt ce que ça signifie sur le terrain. Réponds "
    "en français, dans un style journalistique direct, sans emphase "
    "artificielle."
)


def _to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def motm_report_prompt(motm: dict, all_players: list[dict], events: list[dict] | None = None) -> str:
    ranking_summary = [
        {"name": p["name"], "position": p["position"], "composite_score": p["composite_score"]}
        for p in all_players[:5]
    ]
    events_block = (
        f"\nDéroulé du match (buts, cartons, changements) :\n{_to_json(events)}\n"
        if events
        else ""
    )
    return (
        "Voici le joueur désigné Homme du Match (MOTM) et le top 5 du classement "
        "du match, calculés par le moteur de scoring :\n\n"
        f"MOTM:\n{_to_json(motm)}\n\n"
        f"Top 5 du match:\n{_to_json(ranking_summary)}\n"
        f"{events_block}\n"
        "Rédige un rapport de 3 à 5 phrases expliquant pourquoi ce joueur a "
        "obtenu le meilleur score composite. Si le déroulé du match éclaire "
        "sa performance (action décisive à un moment clé, entré en jeu pour "
        "préserver un score, etc.), relie-le explicitement. Ne te contente "
        "pas de reformuler le breakdown : explique la portée tactique de sa "
        "performance."
    )


def player_analysis_prompt(
    player: dict,
    recent_matches: list[dict] | None = None,
    player_events: list[dict] | None = None,
) -> str:
    context_blocks = []
    if recent_matches:
        context_blocks.append(
            "Forme récente (matchs précédents, du plus ancien au plus récent) :\n"
            f"{_to_json(recent_matches)}"
        )
    if player_events:
        context_blocks.append(
            f"Actions marquantes de ce joueur pendant CE match :\n{_to_json(player_events)}"
        )
    context = ("\n\n" + "\n\n".join(context_blocks)) if context_blocks else ""

    return (
        "Voici les données calculées pour un joueur de ce match :\n\n"
        f"{_to_json(player)}"
        f"{context}\n\n"
        "Rédige une analyse de 2 à 4 phrases. Explique ses points forts et "
        "faibles en les reliant à leur portée tactique réelle plutôt qu'en "
        "citant simplement les catégories. Si une tendance de forme ou une "
        "action marquante est fournie ci-dessus, intègre-la explicitement "
        "(ex : progression, régression, action décisive à un moment clé). "
        "N'introduis jamais de nouveau chiffre."
    )


BLOCK_DELIMITER_TEMPLATE = "[[{key}]]"


def batch_player_analysis_prompt(players: list[dict]) -> str:
    """Un seul prompt pour TOUS les joueurs du match (au lieu d'un appel par joueur).

    Réduit un rapport de ~30 appels LLM séquentiels à un seul appel, ce qui
    évite de saturer le quota du plan gratuit (souvent quelques dizaines de
    requêtes/minute). Le format de sortie ([[player_id]] ... ) est parsé par
    llm/report_generator.py::_parse_batch_blocks.

    Chaque entrée de `players` peut porter en plus des clés optionnelles
    `recent_matches` (forme récente, via persistence.get_player_history) et
    `match_events` (ses actions marquantes dans CE match) — ajoutées par
    report_generator.py quand disponibles.
    """
    slim_players = [
        {k: v for k, v in p.items() if k not in ("radar",)} for p in players
    ]
    example = BLOCK_DELIMITER_TEMPLATE.format(key=players[0]["player_id"]) if players else "[[123]]"
    return (
        "Voici les données calculées (moteur ML) pour TOUS les joueurs de ce "
        "match. Certains portent en plus `recent_matches` (forme récente) et "
        "`match_events` (ses actions marquantes dans ce match) :\n\n"
        f"{_to_json(slim_players)}\n\n"
        "Pour CHAQUE joueur de la liste, rédige une analyse de 2 à 4 phrases. "
        "N'énumère pas simplement les catégories du breakdown — explique ce "
        "que ces chiffres signifient tactiquement, et si `recent_matches` ou "
        "`match_events` sont fournis, relie-les explicitement à l'analyse "
        "(ex : « confirme sa bonne forme des dernières semaines », « son "
        "entrée en jeu a coïncidé avec le renversement du score »). "
        "N'introduis jamais de nouveau chiffre. Réponds STRICTEMENT selon ce "
        "format, un bloc par joueur, sans aucun texte avant/après/entre les "
        "blocs :\n\n"
        f"{example}\n<analyse de ce joueur>\n\n"
        "Répète ce bloc pour CHAQUE player_id de la liste fournie, dans le même ordre, "
        "en remplaçant l'ID entre crochets doubles par le player_id exact du joueur concerné."
    )


def batch_tactical_suggestions_prompt(teams: dict[str, list[dict]]) -> str:
    """Un seul prompt pour LES DEUX équipes (au lieu d'un appel par équipe).

    Les suggestions croisent délibérément les faiblesses des deux équipes
    (style rapport de scouting) plutôt que de ne corriger que les faiblesses
    propres à chaque équipe.
    """
    team_names = list(teams.keys())
    sections = []
    for idx, (team_name, players) in enumerate(teams.items(), start=1):
        weaknesses_summary = [
            {"name": p["name"], "position": p["position"], "weaknesses": p["weaknesses"]}
            for p in players
        ]
        sections.append(f"Équipe {idx} ({team_name}) :\n{_to_json(weaknesses_summary)}")

    opponent_map = (
        f"Équipe 1 = {team_names[0]} ; Équipe 2 = {team_names[1]}."
        if len(team_names) >= 2
        else ""
    )

    return (
        "Voici les points faibles individuels détectés pour les joueurs des "
        "deux équipes de ce match :\n\n" + "\n\n".join(sections) + "\n\n"
        f"{opponent_map}\n\n"
        "Pour CHAQUE équipe, propose 2 à 3 ajustements tactiques concrets "
        "pour le prochain match — mais pas seulement en corrigeant ses "
        "propres faiblesses : raisonne comme un analyste de scouting qui "
        "prépare le prochain adversaire. Quand c'est pertinent, indique "
        "explicitement comment EXPLOITER une faiblesse collective de "
        "l'ADVERSAIRE (ex : « cibler le couloir gauche adverse, où plusieurs "
        "défenseurs affichent une faiblesse en duels »). Ne cite aucune "
        "statistique qui ne figure pas ci-dessus. Réponds STRICTEMENT selon "
        "ce format, sans texte avant/après/entre les blocs :\n\n"
        "[[1]]\n<suggestions équipe 1>\n\n[[2]]\n<suggestions équipe 2>"
    )
