"""Tests de la revue de presse (contexte externe sandboxé, réseau mocké)."""
import pytest

from context import press_bridge


class _Resp:
    def __init__(self, payload):
        self._p = payload
        self.text = '{"ok":1}'

    def json(self):
        return self._p


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # Repart d'un état propre (cache/disjoncteur) et hors mode démo par défaut.
    press_bridge._cache.clear()
    press_bridge._fail_count = 0
    press_bridge._cooldown_until = 0.0
    monkeypatch.setattr(press_bridge, "DEMO_MODE", False)


def _articles(*urls):
    return {"articles": [{"url": u, "title": f"T {u}", "domain": "ex.com", "seendate": "2023"} for u in urls]}


def test_demo_mode_blocks_before_any_network(monkeypatch):
    monkeypatch.setattr(press_bridge, "DEMO_MODE", True)
    called = {"n": 0}
    monkeypatch.setattr(press_bridge._SESSION, "get", lambda *a, **k: called.__setitem__("n", 1))
    with pytest.raises(press_bridge.PressUnavailableError):
        press_bridge.match_press("PSG", "OM")
    assert called["n"] == 0                      # aucune I/O tentée


def test_returns_cited_sources_with_confidence(monkeypatch):
    monkeypatch.setattr(press_bridge._SESSION, "get",
                        lambda *a, **k: _Resp(_articles("https://ex.com/a", "https://ex.com/b")))
    res = press_bridge.match_press("PSG", "Real Madrid", league="UCL", limit=5)
    assert res["confidence"] == "external_unverified"
    assert "non vérifié" in res["disclaimer"]
    assert len(res["sources"]) == 2
    assert res["sources"][0]["url"].startswith("http")
    assert '"PSG"' in res["query"] and '"Real Madrid"' in res["query"]


def test_filters_social_media(monkeypatch):
    monkeypatch.setattr(press_bridge._SESSION, "get",
                        lambda *a, **k: _Resp(_articles("https://twitter.com/x", "https://ex.com/ok")))
    res = press_bridge.match_press("A", "B")
    urls = [s["url"] for s in res["sources"]]
    assert "https://ex.com/ok" in urls
    assert all("twitter.com" not in u for u in urls)


def test_cache_avoids_second_network_call(monkeypatch):
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _Resp(_articles("https://ex.com/a"))

    monkeypatch.setattr(press_bridge._SESSION, "get", fake_get)
    press_bridge.match_press("PSG", "OM")
    press_bridge.match_press("PSG", "OM")          # même requête -> cache
    assert calls["n"] == 1


def test_network_error_raises_unavailable(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr(press_bridge._SESSION, "get", boom)
    with pytest.raises(press_bridge.PressUnavailableError):
        press_bridge.match_press("A", "B")


def test_circuit_breaker_opens_after_repeated_failures(monkeypatch):
    import requests
    monkeypatch.setattr(press_bridge._SESSION, "get",
                        lambda *a, **k: (_ for _ in ()).throw(requests.RequestException("x")))
    for i in range(press_bridge._CB_THRESHOLD):
        with pytest.raises(press_bridge.PressUnavailableError):
            press_bridge.match_press("A", f"B{i}")   # requêtes distinctes (pas de cache)
    # Disjoncteur ouvert : l'appel suivant échoue immédiatement.
    assert press_bridge._breaker_open()
