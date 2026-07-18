"""Modèles SQLAlchemy pour l'historique des matchs analysés."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from persistence.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MatchRecord(Base):
    __tablename__ = "matches"

    fixture_id = Column(Integer, primary_key=True)
    league_name = Column(String)
    league_logo = Column(String)
    date = Column(String)
    venue_name = Column(String)
    home_team_id = Column(Integer)
    home_team_name = Column(String)
    home_team_logo = Column(String)
    away_team_id = Column(Integer)
    away_team_name = Column(String)
    away_team_logo = Column(String)
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    analyzed_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    players = relationship(
        "PlayerScoreRecord", back_populates="match", cascade="all, delete-orphan"
    )
    report = relationship(
        "ReportRecord", back_populates="match", uselist=False, cascade="all, delete-orphan"
    )


class PlayerScoreRecord(Base):
    __tablename__ = "player_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fixture_id = Column(Integer, ForeignKey("matches.fixture_id"), index=True)
    player_id = Column(Integer, index=True)
    name = Column(String)
    photo_url = Column(String)
    team_id = Column(Integer)
    team_name = Column(String)
    team_logo = Column(String)
    position = Column(String)
    minutes = Column(Integer)
    composite_score = Column(Float)
    breakdown_json = Column(Text)
    radar_json = Column(Text)
    strengths_json = Column(Text)
    weaknesses_json = Column(Text)

    match = relationship("MatchRecord", back_populates="players")


class ReportRecord(Base):
    __tablename__ = "reports"

    fixture_id = Column(Integer, ForeignKey("matches.fixture_id"), primary_key=True)
    motm_player_id = Column(Integer)
    motm_report = Column(Text)
    player_reports_json = Column(Text)
    tactical_suggestions_json = Column(Text)
    generated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    match = relationship("MatchRecord", back_populates="report")
