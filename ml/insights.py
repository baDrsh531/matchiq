"""Analytics déterministe : observations automatiques sur un match et lecture
de la forme d'un joueur.

Contrairement au LLM (qui interprète), ces fonctions ne font que **constater**
des faits par règles, à partir des scores déjà calculés. Aucune valeur inventée,
aucun appel réseau/LLM — donc utilisables en mode démo et testables sans mock.
"""
from collections import Counter
from statistics import pstdev

_POSITION_FR = {
    "Goalkeeper": "gardien",
    "Defender": "défenseur",
    "Midfielder": "milieu",
    "Attacker": "attaquant",
}


def match_insights(ranked: list[dict]) -> list[str]:
    """Observations notables sur un match, déduites du classement des scores.

    Chaque règle n'émet un constat que si sa condition est réellement vérifiée.
    Renvoie au plus 4 observations, des plus marquantes aux moins marquantes.
    """
    if not ranked or len(ranked) < 2:
        return []

    out: list[str] = []
    motm, second = ranked[0], ranked[1]
    top5 = ranked[:5]

    # 1. Écart du MOTM sur le reste du classement.
    gap = round(motm["composite_score"] - second["composite_score"], 1)
    if gap >= 1.5:
        out.append(f"{motm['name']} survole le classement : {gap:.1f} pts d'avance sur le 2ᵉ.")

    # 2. Un défenseur/gardien élu homme du match devant tous les attaquants.
    has_attacker_below = any(p["position"] == "Attacker" for p in ranked[1:])
    if motm["position"] in ("Defender", "Goalkeeper") and has_attacker_below:
        out.append(
            f"Le {_POSITION_FR[motm['position']]} {motm['name']} est élu homme du match, "
            "devant tous les attaquants."
        )

    # 3. Un entrant (peu de minutes) qui se hisse dans le top 5.
    sub = next((p for p in top5 if p.get("minutes") and p["minutes"] < 30), None)
    if sub:
        out.append(f"Entré en jeu ({sub['minutes']}′), {sub['name']} se hisse dans le top 5.")

    # 4. Une équipe qui verrouille le haut du classement.
    team, count = Counter(p["team_name"] for p in top5).most_common(1)[0]
    if count >= 4:
        out.append(f"{team} verrouille le match : {count} joueurs dans le top 5.")

    # 5. Un carton rouge chez un joueur pourtant bien classé.
    upper_half = ranked[: max(3, len(ranked) // 2)]
    sent_off = next((p for p in upper_half if p.get("breakdown", {}).get("cards_red", 0) < 0), None)
    if sent_off:
        out.append(f"{sent_off['name']} a été expulsé malgré une prestation notable.")

    return out[:4]


def form_summary(matches: list[dict]) -> dict | None:
    """Lecture déterministe de la forme d'un joueur sur ses matchs analysés.

    `matches` est ordonné du plus ancien au plus récent (comme
    persistence.get_player_history). Renvoie la tendance, le meilleur/pire match
    et la régularité — ou un état « un seul match » quand il n'y a pas assez de
    recul pour parler de tendance.
    """
    scored = [m for m in matches if m.get("composite_score") is not None]
    if not scored:
        return None

    scores = [m["composite_score"] for m in scored]
    best = max(scored, key=lambda m: m["composite_score"])
    worst = min(scored, key=lambda m: m["composite_score"])

    if len(scores) == 1:
        return {"trend": "single", "label": "Un seul match analysé", "best": None, "worst": None, "consistency": None}

    delta = scores[-1] - scores[0]
    if delta >= 1.0:
        trend, label = "up", "En progression"
    elif delta <= -1.0:
        trend, label = "down", "En perte de vitesse"
    else:
        trend, label = "stable", "Régulier"

    return {
        "trend": trend,
        "label": label,
        "best": {"score": round(best["composite_score"], 1), "opponent": best.get("opponent_name")},
        "worst": {"score": round(worst["composite_score"], 1), "opponent": worst.get("opponent_name")},
        "consistency": "régulier" if pstdev(scores) < 1.0 else "en dents de scie",
    }
