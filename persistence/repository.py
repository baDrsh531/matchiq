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
