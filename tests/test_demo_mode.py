"""Vérifie que le mode démo coupe réellement tout appel sortant.

L'enjeu est une instance publique : n'importe qui peut appeler n'importe quelle
route, donc il ne doit exister aucun chemin permettant de consommer le quota
API-Football ou de déclencher une facturation Gemini.
"""
import json

import pytest

from llm import llm_client
from ml import ingestion


@pytest.fixture
def demo_on(monkeypatch):
    monkeypatch.setattr(ingestion, "DEMO_MODE", True)
    monkeypatch.setattr(llm_client, "DEMO_MODE", True)


@pytest.fixture
def no_network(monkeypatch):
    """Tout appel réseau réel fait échouer le test bruyamment."""
    def interdit(*args, **kwargs):
        raise AssertionError("appel réseau sortant alors que le mode démo est actif")

    monkeypatch.setattr(ingestion.requests, "get", interdit)


# --------------------------------------------------------------------------
# API-Football
# --------------------------------------------------------------------------

def test_get_bloque_avant_tout_appel_reseau(demo_on, no_network):
    with pytest.raises(ingestion.DemoModeError):
        ingestion._get("fixtures", {"id": 1})


def test_demo_mode_error_est_une_api_football_error(demo_on):
    """Garantit la traduction en 503 par les routers, sans code supplémentaire."""
    assert issubclass(ingestion.DemoModeError, ingestion.ApiFootballError)


@pytest.mark.parametrize(
    "fonction, args",
    [
        (lambda: ingestion.fetch_fixture_info(1), ()),
        (lambda: ingestion.fetch_fixture_players(1), ()),
        (lambda: ingestion.fetch_fixture_events(1), ()),
        (lambda: ingestion.fetch_fixture_lineups(1), ()),
        (lambda: ingestion.fetch_fixture_statistics(1), ()),
    ],
)
def test_aucun_endpoint_ne_contourne_le_verrou(demo_on, no_network, fonction, args):
    with pytest.raises(ingestion.ApiFootballError):
        fonction()


def test_le_cache_disque_reste_servi(demo_on, no_network, tmp_path, monkeypatch):
    """Le mode démo bloque le réseau mais ne casse pas la lecture du cache."""
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    # les 5 clés attendues par _REQUIRED_KEYS, sinon fetch_fixture complète
    # le cache en appelant l'API — ce que le mode démo doit justement bloquer
    cache = {
        "fixture_id": 42,
        "fixture": {"fixture": {"id": 42}},
        "statistics": [],
        "players": [],
        "events": [],
        "lineups": [],
    }
    (tmp_path / "42.json").write_text(json.dumps(cache), encoding="utf-8")

    resultat = ingestion.fetch_fixture(42)
    assert resultat["fixture"]["fixture"]["id"] == 42


def test_cache_incomplet_ne_declenche_pas_dappel(demo_on, no_network, tmp_path, monkeypatch):
    """Un cache partiel doit échouer proprement, pas tenter de se compléter."""
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    (tmp_path / "43.json").write_text(json.dumps({"fixture_id": 43}), encoding="utf-8")

    with pytest.raises(ingestion.DemoModeError):
        ingestion.fetch_fixture(43)


# --------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------

def test_generation_llm_refusee(demo_on):
    with pytest.raises(RuntimeError, match="[Mm]ode démo"):
        llm_client.generate_report("Analyse ce match.")


def test_generation_llm_ne_construit_pas_de_client(demo_on, monkeypatch):
    """Le refus doit précéder toute initialisation du SDK, donc toute clé lue."""
    def interdit():
        raise AssertionError("client Gemini instancié alors que le mode démo est actif")

    monkeypatch.setattr(llm_client, "_get_client", interdit)
    with pytest.raises(RuntimeError):
        llm_client.generate_report("Analyse ce match.")


# --------------------------------------------------------------------------
# Comportement par défaut
# --------------------------------------------------------------------------

def test_mode_demo_desactive_par_defaut():
    """Un oubli de configuration ne doit jamais brider une instance locale."""
    import config

    assert config.DEMO_MODE is False


@pytest.mark.parametrize("valeur, attendu", [
    ("1", True), ("true", True), ("TRUE", True), ("yes", True), ("on", True),
    ("0", False), ("false", False), ("", False), ("nope", False),
])
def test_lecture_de_la_variable_denvironnement(monkeypatch, valeur, attendu):
    monkeypatch.setenv("DEMO_MODE", valeur)
    import importlib

    import config

    importlib.reload(config)
    assert config.DEMO_MODE is attendu
    monkeypatch.delenv("DEMO_MODE", raising=False)
    importlib.reload(config)
