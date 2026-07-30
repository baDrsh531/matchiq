"""Modèle Elo déterministe pour la prédiction pré-match.

Dans l'esprit du reste du projet — *le ML calcule, le LLM interprète* — ce module
produit une probabilité de victoire AVANT le match, à partir des seuls résultats
passés (aucune donnée future, aucun appel modèle). Le LLM commente ensuite la
prédiction face au résultat réel.

Le classement Elo résume la force d'une équipe en un nombre : après chaque match,
le gagnant prend des points au perdant, d'autant plus que le résultat était
inattendu. On y ajoute deux éléments propres au football :

  * un avantage à domicile (``HOME_ADVANTAGE`` points ajoutés à l'équipe qui
    reçoit au moment du calcul de la probabilité) ;
  * un modèle de nul explicite : l'Elo classique ne donne qu'une *espérance de
    points* (victoire = 1, nul = 0,5, défaite = 0). Pour en tirer trois
    probabilités (V/N/D), on modélise la probabilité de nul comme maximale quand
    les équipes sont de force égale et décroissante quand l'écart se creuse.

Rien ici n'est ajusté sur les données futures : les probabilités se lisent en
*walk-forward* (on prédit un match avec les notes calculées AVANT lui), ce qui
rend le score de Brier (``brier_score``) honnête plutôt que flatteur.
"""
from __future__ import annotations

from typing import Iterable, Optional

BASE_RATING = 1500.0
K_FACTOR = 20.0
HOME_ADVANTAGE = 65.0          # points Elo, ordre de grandeur classique au foot
DRAW_MAX = 0.28                # taux de nul quand les équipes sont à égalité parfaite


def expected_score(rating_home: float, rating_away: float,
                   home_advantage: float = HOME_ADVANTAGE) -> float:
    """Espérance de points de l'équipe à domicile (0 = défaite certaine, 1 = victoire
    certaine, 0,5 = équilibre), avantage du terrain inclus."""
    diff = (rating_away - (rating_home + home_advantage)) / 400.0
    return 1.0 / (1.0 + 10.0 ** diff)


def _result_score(home_goals: int, away_goals: int) -> float:
    """Points marqués par l'équipe à domicile : 1 victoire, 0,5 nul, 0 défaite."""
    if home_goals > away_goals:
        return 1.0
    if home_goals < away_goals:
        return 0.0
    return 0.5


def update_ratings(rating_home: float, rating_away: float,
                   home_goals: int, away_goals: int,
                   k: float = K_FACTOR) -> tuple[float, float]:
    """Nouvelles notes des deux équipes après un match (somme des points conservée)."""
    exp_home = expected_score(rating_home, rating_away)
    actual_home = _result_score(home_goals, away_goals)
    delta = k * (actual_home - exp_home)
    return rating_home + delta, rating_away - delta


def win_draw_loss(expected_home: float, draw_max: float = DRAW_MAX) -> tuple[float, float, float]:
    """Décompose une espérance de points en (P(victoire domicile), P(nul), P(victoire extérieur)).

    Modèle de nul : ``d = draw_max * (1 - |2·E - 1|)`` — maximal à l'équilibre
    (E = 0,5), nul quand un camp est écrasant. On répartit ensuite le reste en
    respectant l'identité ``P(victoire) + 0,5·P(nul) = E`` (l'espérance de points
    doit rester cohérente avec le classement).
    """
    e = min(1.0, max(0.0, expected_home))
    draw = draw_max * (1.0 - abs(2.0 * e - 1.0))
    home = e - draw / 2.0
    away = 1.0 - home - draw
    # Garde-fous numériques aux extrêmes (E proche de 0 ou 1).
    home = max(0.0, home)
    away = max(0.0, away)
    total = home + draw + away
    return home / total, draw / total, away / total


class EloModel:
    """Classement Elo construit par passages successifs sur des matchs terminés.

    Usage :
        model = EloModel()
        model.fit(fixtures)                  # fixtures triés ou non, on les trie
        proba = model.predict(home_id, away_id)   # {'home':.., 'draw':.., 'away':..}
    """

    def __init__(self, base: float = BASE_RATING, k: float = K_FACTOR,
                 draw_max: float = DRAW_MAX):
        self.base = base
        self.k = k
        self.draw_max = draw_max
        self.ratings: dict[int, float] = {}
        self.names: dict[int, str] = {}
        self.games: dict[int, int] = {}   # nb de matchs vus par équipe (fiabilité)
        self.last_result: Optional[dict] = None

    def rating(self, team_id: int) -> float:
        return self.ratings.get(team_id, self.base)

    def _observe(self, fx: dict) -> Optional[tuple]:
        """Extrait (home_id, away_id, home_goals, away_goals, date, names) d'un fixture
        API-Football terminé, ou None s'il est inexploitable."""
        status = fx.get("fixture", {}).get("status", {}).get("short")
        if status not in ("FT", "AET", "PEN"):
            return None
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        home, away = teams.get("home", {}), teams.get("away", {})
        hid, aid = home.get("id"), away.get("id")
        hg, ag = goals.get("home"), goals.get("away")
        if hid is None or aid is None or hg is None or ag is None:
            return None
        date = fx.get("fixture", {}).get("date", "")
        return hid, aid, int(hg), int(ag), date, home.get("name"), away.get("name")

    def fit(self, fixtures: Iterable[dict]) -> "EloModel":
        """Met à jour les notes en parcourant les matchs par ordre chronologique."""
        observed = [o for o in (self._observe(fx) for fx in fixtures) if o]
        observed.sort(key=lambda o: o[4])  # tri par date croissante
        for hid, aid, hg, ag, _date, hname, aname in observed:
            if hname:
                self.names[hid] = hname
            if aname:
                self.names[aid] = aname
            rh, ra = self.rating(hid), self.rating(aid)
            nh, na = update_ratings(rh, ra, hg, ag, k=self.k)
            self.ratings[hid], self.ratings[aid] = nh, na
            self.games[hid] = self.games.get(hid, 0) + 1
            self.games[aid] = self.games.get(aid, 0) + 1
        return self

    def predict(self, home_id: int, away_id: int) -> dict:
        """Probabilités V/N/D pour un match à venir entre deux équipes connues."""
        rh, ra = self.rating(home_id), self.rating(away_id)
        e = expected_score(rh, ra)
        home, draw, away = win_draw_loss(e, draw_max=self.draw_max)
        return {
            "home": round(home, 4),
            "draw": round(draw, 4),
            "away": round(away, 4),
            "rating_home": round(rh, 1),
            "rating_away": round(ra, 1),
            "rating_diff": round(rh - ra, 1),
            "games_home": self.games.get(home_id, 0),
            "games_away": self.games.get(away_id, 0),
        }


def brier_score(fixtures: Iterable[dict], base: float = BASE_RATING,
                k: float = K_FACTOR, draw_max: float = DRAW_MAX) -> dict:
    """Score de Brier multi-classe en walk-forward — mesure honnête de calibration.

    Pour chaque match pris dans l'ordre : on prédit V/N/D avec les notes calculées
    AVANT ce match, on mesure l'écart quadratique au résultat réel (one-hot), PUIS
    on met à jour les notes. Le modèle ne voit jamais le résultat qu'il prédit.

    Renvoie ``{'brier': .., 'baseline': .., 'skill': .., 'n': ..}`` où la baseline
    est la prédiction constante (taux V/N/D moyens) et ``skill`` la réduction
    relative d'erreur par rapport à elle (>0 = mieux que « toujours la moyenne »).
    """
    model = EloModel(base=base, k=k, draw_max=draw_max)
    observed = [o for o in (model._observe(fx) for fx in fixtures) if o]
    observed.sort(key=lambda o: o[4])

    outcomes: list[tuple[float, float, float]] = []   # one-hot réels
    preds: list[tuple[float, float, float]] = []
    for hid, aid, hg, ag, _date, hname, aname in observed:
        if hname:
            model.names[hid] = hname
        if aname:
            model.names[aid] = aname
        e = expected_score(model.rating(hid), model.rating(aid))
        preds.append(win_draw_loss(e, draw_max=draw_max))
        if hg > ag:
            oh = (1.0, 0.0, 0.0)
        elif hg == ag:
            oh = (0.0, 1.0, 0.0)
        else:
            oh = (0.0, 0.0, 1.0)
        outcomes.append(oh)
        rh, ra = update_ratings(model.rating(hid), model.rating(aid), hg, ag, k=k)
        model.ratings[hid], model.ratings[aid] = rh, ra

    n = len(outcomes)
    if n == 0:
        return {"brier": None, "baseline": None, "skill": None, "n": 0}

    def _mean_brier(prediction_of):
        total = 0.0
        for i in range(n):
            p = prediction_of(i)
            o = outcomes[i]
            total += sum((p[j] - o[j]) ** 2 for j in range(3))
        return total / n

    brier = _mean_brier(lambda i: preds[i])
    rates = tuple(sum(o[j] for o in outcomes) / n for j in range(3))  # V/N/D moyens
    baseline = _mean_brier(lambda _i: rates)
    skill = (baseline - brier) / baseline if baseline else 0.0
    return {"brier": round(brier, 4), "baseline": round(baseline, 4),
            "skill": round(skill, 4), "n": n, "base_rates": [round(r, 3) for r in rates]}
