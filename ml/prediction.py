"""Service de prédiction pré-match : construit un classement Elo depuis les
résultats d'une ligue-saison et en tire des probabilités V/N/D.

Deux modes :
  * ``predict_matchup`` — pronostic d'une affiche à venir avec les notes de fin
    de période (usage « qui gagnerait si ces deux équipes se rencontraient ? ») ;
  * ``predict_fixture`` — pronostic HONNÊTE d'un match déjà joué : on n'entraîne
    l'Elo que sur les matchs ANTÉRIEURS à sa date, puis on compare la prédiction
    au résultat réel. C'est ce mode que le LLM commente.

Le modèle Elo est mis en cache en mémoire par (ligue, saison) : le reconstruire
à chaque requête serait inutile puisqu'il ne dépend que des fixtures en cache.
"""
from __future__ import annotations

import threading
from typing import Optional

from ml.elo import EloModel, brier_score
from ml.ingestion import fetch_league_fixtures

_model_cache: dict[tuple[int, int], EloModel] = {}
_brier_cache: dict[tuple[int, int], dict] = {}
_lock = threading.Lock()


def _model_for(league_id: int, season: int) -> EloModel:
    key = (league_id, season)
    with _lock:
        if key not in _model_cache:
            fixtures = fetch_league_fixtures(league_id, season)
            _model_cache[key] = EloModel().fit(fixtures)
        return _model_cache[key]


def _resolve_team(model: EloModel, team: int | str) -> Optional[int]:
    """Accepte un id numérique ou un nom (sous-chaîne insensible à la casse)."""
    try:
        tid = int(team)
        return tid if tid in model.ratings else None
    except (TypeError, ValueError):
        needle = str(team).strip().lower()
        matches = [tid for tid, name in model.names.items()
                   if needle and needle in (name or "").lower()]
        return matches[0] if len(matches) == 1 else (matches[0] if matches else None)


def predict_matchup(league_id: int, season: int, home: int | str, away: int | str) -> dict:
    """Pronostic d'une affiche avec les notes de fin de saison. ``home``/``away``
    peuvent être des id ou des noms d'équipe."""
    model = _model_for(league_id, season)
    hid, aid = _resolve_team(model, home), _resolve_team(model, away)
    if hid is None or aid is None:
        unknown = home if hid is None else away
        raise ValueError(f"Équipe introuvable dans {league_id}/{season} : {unknown!r}")
    proba = model.predict(hid, aid)
    proba["home_name"] = model.names.get(hid, str(hid))
    proba["away_name"] = model.names.get(aid, str(aid))
    proba["league_id"] = league_id
    proba["season"] = season
    return proba


def predict_fixture(league_id: int, season: int, fixture_id: int) -> dict:
    """Pronostic pré-match d'un match précis, entraîné uniquement sur les matchs
    ANTÉRIEURS à sa date, puis confronté au résultat réel (si le match est joué).

    C'est la brique clé du récit « prédit avant, vérifié après » : le modèle ne
    voit jamais le résultat qu'il annonce.
    """
    fixtures = fetch_league_fixtures(league_id, season)
    target = next((f for f in fixtures if f.get("fixture", {}).get("id") == fixture_id), None)
    if target is None:
        raise ValueError(f"Match {fixture_id} absent de {league_id}/{season}.")

    target_date = target.get("fixture", {}).get("date", "")
    past = [f for f in fixtures if f.get("fixture", {}).get("date", "") < target_date]
    model = EloModel().fit(past)

    teams = target.get("teams", {})
    hid = teams.get("home", {}).get("id")
    aid = teams.get("away", {}).get("id")
    proba = model.predict(hid, aid)
    proba["home_name"] = teams.get("home", {}).get("name")
    proba["away_name"] = teams.get("away", {}).get("name")
    proba["date"] = target_date
    proba["fixture_id"] = fixture_id
    proba["trained_on"] = len(past)

    goals = target.get("goals", {})
    hg, ag = goals.get("home"), goals.get("away")
    status = target.get("fixture", {}).get("status", {}).get("short")
    if status in ("FT", "AET", "PEN") and hg is not None and ag is not None:
        actual = "home" if hg > ag else ("away" if ag > hg else "draw")
        predicted = max(("home", "draw", "away"), key=lambda k: proba[k])
        proba["result"] = {
            "home_goals": hg, "away_goals": ag,
            "outcome": actual,
            "predicted": predicted,
            "hit": actual == predicted,          # la prédiction la + probable est-elle tombée ?
            "prob_of_actual": proba[actual],     # proba assignée au résultat réel
        }
    return proba


def league_table(league_id: int, season: int) -> dict:
    """Classement Elo trié + calibration (Brier) de la ligue-saison."""
    model = _model_for(league_id, season)
    key = (league_id, season)
    with _lock:
        if key not in _brier_cache:
            _brier_cache[key] = brier_score(fetch_league_fixtures(league_id, season))
        cal = _brier_cache[key]
    ranked = sorted(model.ratings.items(), key=lambda kv: -kv[1])
    return {
        "league_id": league_id,
        "season": season,
        "calibration": cal,
        "teams": [
            {"team_id": tid, "name": model.names.get(tid, str(tid)),
             "rating": round(r, 1), "games": model.games.get(tid, 0)}
            for tid, r in ranked
        ],
    }
