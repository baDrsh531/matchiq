"""Connexion SQLite (SQLAlchemy) — stocke l'historique des matchs analysés,
les scores composites calculés et les rapports LLM générés.

Distinct du cache fichier de ml/ingestion.py (qui cache les réponses BRUTES
de l'API-Football pour préserver le quota) : cette base stocke les RÉSULTATS
déjà calculés, pour permettre de parcourir l'historique des matchs analysés
sans refaire tourner le moteur de scoring ni régénérer les rapports.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db() -> None:
    """Crée les tables si elles n'existent pas déjà. Appelé au démarrage de l'API."""
    from persistence import models  # noqa: F401  (enregistre les modèles sur Base)

    Base.metadata.create_all(bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
