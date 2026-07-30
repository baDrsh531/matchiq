"""Écriture/lecture de l'historique des matchs analysés (SQLite).

Les routes API restent la source de vérité "live" (ingestion + scoring
recalculés à chaque appel, vite grâce au cache fichier) ; cette couche
persiste simplement un instantané des résultats pour l'historique
(page "matchs récents") sans jamais être un chemin de lecture obligatoire.
"""
import json

from sqlalchemy.orm import Session

from persistence.models import MatchRecord, PlayerScoreRecord, ReportRecord


def save_match_snapshot(session: Session, match_info: dict, players: list[dict]) -> None:
    fixture_id = match_info["fixture_id"]
    teams = match_info.get("teams") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    goals = match_info.get("goals") or {}
    league = match_info.get("league") or {}
    venue = match_info.get("venue") or {}

    record = session.get(MatchRecord, fixture_id)
    if record is None:
        record = MatchRecord(fixture_id=fixture_id)
        session.add(record)

    record.league_name = league.get("name")
    record.league_logo = league.get("logo")
    record.date = match_info.get("date")
    record.venue_name = venue.get("name")
    record.home_team_id = home.get("id")
    record.home_team_name = home.get("name")
    record.home_team_logo = home.get("logo")
    record.away_team_id = away.get("id")
    record.away_team_name = away.get("name")
    record.away_team_logo = away.get("logo")
    record.home_goals = goals.get("home")
    record.away_goals = goals.get("away")

    # on remplace les scores joueurs existants par le nouveau calcul
    session.query(PlayerScoreRecord).filter(
        PlayerScoreRecord.fixture_id == fixture_id
    ).delete()
    for player in players:
        session.add(
            PlayerScoreRecord(
                fixture_id=fixture_id,
                player_id=player["player_id"],
                name=player["name"],
                photo_url=player.get("photo_url"),
                team_id=player["team_id"],
                team_name=player["team_name"],
                team_logo=player.get("team_logo"),
                position=player["position"],
                minutes=player["minutes"],
                composite_score=player["composite_score"],
                breakdown_json=json.dumps(player["breakdown"], ensure_ascii=False),
                radar_json=json.dumps(player["radar"], ensure_ascii=False),
                strengths_json=json.dumps(player["strengths"], ensure_ascii=False),
                weaknesses_json=json.dumps(player["weaknesses"], ensure_ascii=False),
            )
        )
    session.commit()


def save_report(session: Session, fixture_id: int, report: dict, motm_player_id: int | None) -> None:
    record = session.get(ReportRecord, fixture_id)
    if record is None:
        record = ReportRecord(fixture_id=fixture_id)
        session.add(record)

    record.motm_player_id = motm_player_id
    record.motm_report = report.get("motm_report")
    record.player_reports_json = json.dumps(report.get("player_reports", {}), ensure_ascii=False)
    record.tactical_suggestions_json = json.dumps(
        report.get("tactical_suggestions", {}), ensure_ascii=False
    )
    session.commit()


def get_player_history(session: Session, player_id: int) -> dict | None:
    """Agrège les performances d'un joueur sur tous les matchs analysés (DB uniquement,
    aucun appel API-Football supplémentaire) : vue "carrière" pour la fiche joueur."""
    records = (
        session.query(PlayerScoreRecord)
        .filter(PlayerScoreRecord.player_id == player_id)
        .all()
    )
    if not records:
        return None

    pairs = [(r, session.get(MatchRecord, r.fixture_id)) for r in records]
    pairs.sort(key=lambda pair: (pair[1].date if pair[1] and pair[1].date else ""))

    matches = []
    for record, match in pairs:
        opponent_name = None
        if match:
            opponent_name = (
                match.away_team_name if match.home_team_id == record.team_id else match.home_team_name
            )
        matches.append(
            {
                "fixture_id": record.fixture_id,
                "date": match.date if match else None,
                "opponent_name": opponent_name,
                "composite_score": record.composite_score,
                "position": record.position,
                "minutes": record.minutes,
            }
        )

    latest = pairs[-1][0]
    average_score = round(sum(r.composite_score for r in records) / len(records), 2)

    return {
        "player_id": player_id,
        "name": latest.name,
        "photo_url": latest.photo_url,
        "team_id": latest.team_id,
        "team_name": latest.team_name,
        "team_logo": latest.team_logo,
        "position": latest.position,
        "radar": json.loads(latest.radar_json) if latest.radar_json else {},
        "average_score": average_score,
        "matches_played": len(records),
        "matches": matches,
    }


def get_team_history(session: Session, team_id: int) -> dict | None:
    """Agrège les matchs et l'effectif observé d'une équipe (DB uniquement) : vue
    "club" pour la fiche équipe, sans nouvel appel API-Football."""
    match_records = (
        session.query(MatchRecord)
        .filter((MatchRecord.home_team_id == team_id) | (MatchRecord.away_team_id == team_id))
        .order_by(MatchRecord.date)
        .all()
    )
    if not match_records:
        return None

    team_name = None
    team_logo = None
    matches = []
    for m in match_records:
        if m.home_team_id == team_id:
            team_name, team_logo = m.home_team_name, m.home_team_logo
            opponent_name, goals_for, goals_against = m.away_team_name, m.home_goals, m.away_goals
        else:
            team_name, team_logo = m.away_team_name, m.away_team_logo
            opponent_name, goals_for, goals_against = m.home_team_name, m.away_goals, m.home_goals
        matches.append(
            {
                "fixture_id": m.fixture_id,
                "date": m.date,
                "opponent_name": opponent_name,
                "goals_for": goals_for,
                "goals_against": goals_against,
            }
        )

    player_rows = (
        session.query(PlayerScoreRecord).filter(PlayerScoreRecord.team_id == team_id).all()
    )
    squad_by_player: dict[int, dict] = {}
    for p in player_rows:
        entry = squad_by_player.setdefault(
            p.player_id,
            {
                "player_id": p.player_id,
                "name": p.name,
                "photo_url": p.photo_url,
                "position": p.position,
                "appearances": 0,
                "total_score": 0.0,
            },
        )
        entry["appearances"] += 1
        entry["total_score"] += p.composite_score

    squad = sorted(
        (
            {
                "player_id": e["player_id"],
                "name": e["name"],
                "photo_url": e["photo_url"],
                "position": e["position"],
                "appearances": e["appearances"],
                "average_score": round(e["total_score"] / e["appearances"], 2),
            }
            for e in squad_by_player.values()
        ),
        key=lambda s: s["average_score"],
        reverse=True,
    )

    return {
        "team_id": team_id,
        "team_name": team_name,
        "team_logo": team_logo,
        "matches": matches,
        "squad": squad,
    }


def list_matches(session: Session, limit: int = 50) -> list[dict]:
    records = (
        session.query(MatchRecord)
        .order_by(MatchRecord.analyzed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "fixture_id": r.fixture_id,
            "league_name": r.league_name,
            "league_logo": r.league_logo,
            "date": r.date,
            "home_team": {"id": r.home_team_id, "name": r.home_team_name, "logo": r.home_team_logo},
            "away_team": {"id": r.away_team_id, "name": r.away_team_name, "logo": r.away_team_logo},
            "goals": {"home": r.home_goals, "away": r.away_goals},
            "has_report": r.report is not None,
            "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else None,
        }
        for r in records
    ]


def available_positions(session: Session) -> list[str]:
    """Postes présents dans les performances enregistrées (pour un filtre)."""
    rows = session.query(PlayerScoreRecord.position).distinct().all()
    return sorted(r[0] for r in rows if r[0])


def player_profiles(session: Session, position: str | None = None) -> list[dict]:
    """Profil statistique moyen de chaque joueur, agrégé sur tous ses matchs.

    Sert de vecteur de comparaison pour la recherche de joueurs au style proche :
    chaque joueur est résumé par la moyenne de ses contributions `breakdown` (les
    catégories dépendent du poste, d'où le filtre `position`). Un seul instantané
    par joueur — on moyenne quand il a plusieurs matchs."""
    query = session.query(PlayerScoreRecord)
    if position:
        query = query.filter(PlayerScoreRecord.position == position)

    by_player: dict[int, dict] = {}
    for r in query.all():
        breakdown = json.loads(r.breakdown_json) if r.breakdown_json else {}
        entry = by_player.setdefault(r.player_id, {
            "player_id": r.player_id, "name": r.name, "photo_url": r.photo_url,
            "team_id": r.team_id, "team_name": r.team_name, "position": r.position,
            "appearances": 0, "score_sum": 0.0, "breakdown_sum": {},
        })
        entry["name"], entry["photo_url"] = r.name, r.photo_url          # garde le + récent
        entry["team_id"], entry["team_name"] = r.team_id, r.team_name
        entry["appearances"] += 1
        entry["score_sum"] += r.composite_score or 0.0
        for k, v in breakdown.items():
            entry["breakdown_sum"][k] = entry["breakdown_sum"].get(k, 0.0) + float(v)

    profiles = []
    for e in by_player.values():
        n = e["appearances"]
        profiles.append({
            "player_id": e["player_id"], "name": e["name"], "photo_url": e["photo_url"],
            "team_id": e["team_id"], "team_name": e["team_name"], "position": e["position"],
            "appearances": n,
            "average_score": round(e["score_sum"] / n, 2) if n else 0.0,
            "breakdown": {k: v / n for k, v in e["breakdown_sum"].items()},
        })
    return profiles


def top_performances(session: Session, limit: int = 20, position: str | None = None) -> list[dict]:
    """Palmarès : meilleures performances individuelles (score composite d'un
    joueur sur un match) parmi tous les matchs analysés. DB uniquement, aucun
    appel API-Football. Filtrable par poste."""
    query = session.query(PlayerScoreRecord)
    if position:
        query = query.filter(PlayerScoreRecord.position == position)
    rows = query.order_by(PlayerScoreRecord.composite_score.desc()).limit(limit).all()

    result = []
    for r in rows:
        match = session.get(MatchRecord, r.fixture_id)
        opponent_name = date = None
        if match:
            opponent_name = (
                match.away_team_name if match.home_team_id == r.team_id else match.home_team_name
            )
            date = match.date
        result.append(
            {
                "player_id": r.player_id,
                "name": r.name,
                "photo_url": r.photo_url,
                "team_name": r.team_name,
                "team_logo": r.team_logo,
                "position": r.position,
                "composite_score": r.composite_score,
                "minutes": r.minutes,
                "fixture_id": r.fixture_id,
                "opponent_name": opponent_name,
                "date": date,
            }
        )
    return result


def _match_card(session: Session, fixture_id: int) -> dict | None:
    """Résumé d'un match analysé (pour le comparateur), avec les scores joueurs."""
    match = session.get(MatchRecord, fixture_id)
    if match is None:
        return None
    rows = (
        session.query(PlayerScoreRecord)
        .filter(PlayerScoreRecord.fixture_id == fixture_id)
        .order_by(PlayerScoreRecord.composite_score.desc())
        .all()
    )
    card = {
        "fixture_id": fixture_id,
        "date": match.date,
        "league_name": match.league_name,
        "home_team": {"id": match.home_team_id, "name": match.home_team_name, "logo": match.home_team_logo},
        "away_team": {"id": match.away_team_id, "name": match.away_team_name, "logo": match.away_team_logo},
        "goals": {"home": match.home_goals, "away": match.away_goals},
        "motm": (
            {"player_id": rows[0].player_id, "name": rows[0].name, "composite_score": rows[0].composite_score}
            if rows
            else None
        ),
        "top_players": [
            {"player_id": r.player_id, "name": r.name, "position": r.position, "composite_score": r.composite_score}
            for r in rows[:5]
        ],
    }
    return card, {r.player_id: r for r in rows}


def compare_matches(session: Session, fixture_a: int, fixture_b: int) -> dict | None:
    """Compare deux matchs déjà analysés : leurs cartes respectives et les
    joueurs COMMUNS aux deux (avec l'écart de note d'un match à l'autre).
    DB uniquement, aucun appel API-Football."""
    a = _match_card(session, fixture_a)
    b = _match_card(session, fixture_b)
    if a is None or b is None:
        return None
    card_a, scores_a = a
    card_b, scores_b = b

    common = []
    for pid, ra in scores_a.items():
        rb = scores_b.get(pid)
        if rb is None:
            continue
        common.append(
            {
                "player_id": pid,
                "name": ra.name,
                "position": ra.position,
                "photo_url": ra.photo_url,
                "score_a": ra.composite_score,
                "score_b": rb.composite_score,
                "delta": round(rb.composite_score - ra.composite_score, 2),
            }
        )
    common.sort(key=lambda c: c["score_a"], reverse=True)
    return {"match_a": card_a, "match_b": card_b, "common_players": common}


def search_players(session: Session, query: str, limit: int = 20) -> list[dict]:
    """Recherche par nom parmi les joueurs déjà analysés (DB uniquement,
    aucun appel API-Football — complète la recherche d'équipe côté live API)."""
    rows = (
        session.query(PlayerScoreRecord)
        .filter(PlayerScoreRecord.name.ilike(f"%{query}%"))
        .order_by(PlayerScoreRecord.name)
        .all()
    )
    seen: dict[int, dict] = {}
    for r in rows:
        seen.setdefault(
            r.player_id,
            {
                "player_id": r.player_id,
                "name": r.name,
                "photo_url": r.photo_url,
                "team_name": r.team_name,
                "team_logo": r.team_logo,
            },
        )
    return list(seen.values())[:limit]
