"""Tests de la fiche de scouting (assemblage déterministe + PDF)."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from persistence.database import Base
from persistence.repository import save_match_snapshot
from reporting.pdf_report import build_scouting_pdf
from reporting.scouting import build_scouting_data


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


def _match(fixture_id, players):
    return {
        "fixture_id": fixture_id,
        "teams": {"home": {"id": 1, "name": "A", "logo": ""}, "away": {"id": 2, "name": "B", "logo": ""}},
        "goals": {"home": 1, "away": 0}, "date": f"2023-01-{fixture_id:02d}",
        "venue": {"name": "V"}, "league": {"name": "L", "logo": ""},
    }


def _player(pid, name, tackles, passes, score=6.0):
    return {
        "player_id": pid, "name": name, "photo_url": "", "team_id": 1, "team_name": "A",
        "team_logo": "", "position": "Defender", "minutes": 90, "composite_score": score,
        "breakdown": {"tackles": tackles, "passes_accuracy": passes, "cards_yellow": 1},
        "radar": {}, "strengths": [], "weaknesses": [],
    }


def _seed(session):
    save_match_snapshot(session, _match(1, None), [
        _player(10, "Cible", tackles=0.9, passes=0.2, score=8.0),
        _player(20, "Autre1", tackles=0.3, passes=0.6, score=6.0),
        _player(30, "Autre2", tackles=0.2, passes=0.7, score=5.0),
    ])


def test_build_scouting_data_none_for_unknown(session):
    assert build_scouting_data(session, 999) is None


def test_scouting_data_computes_baseline_and_summary(session):
    _seed(session)
    data = build_scouting_data(session, 10)
    assert data["player"]["name"] == "Cible"
    assert data["baseline_n"] == 2                      # deux autres défenseurs
    # La cible tacle plus que la moyenne -> "tackles" en force, pas en faiblesse.
    assert "tackles" in data["strengths"]
    assert "au-dessus de" in data["exec_summary"]
    # Les cartons (catégorie négative) ne doivent jamais compter comme force.
    assert "cards_yellow" not in data["strengths"]


def test_scouting_pdf_is_valid_pdf(session):
    _seed(session)
    data = build_scouting_data(session, 10)
    pdf = build_scouting_pdf(data, lang="fr")
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_scouting_pdf_english(session):
    _seed(session)
    data = build_scouting_data(session, 10)
    pdf = build_scouting_pdf(data, lang="en")
    assert pdf[:5] == b"%PDF-"
