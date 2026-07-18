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
