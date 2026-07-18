import json
from types import SimpleNamespace

import pytest

from ml import ingestion


class _FakeResponse:
    def __init__(self, json_data, status_code=200, headers=None):
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}
        self.text = json.dumps(json_data)

    def json(self):
        return self._json_data


def test_fetch_fixture_uses_cache_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    cache_file = tmp_path / "12345.json"
    cached_payload = {"fixture_id": 12345, "fixture": {}, "statistics": [], "players": [], "events": []}
    cache_file.write_text(json.dumps(cached_payload), encoding="utf-8")

    def fail_get(*args, **kwargs):
        raise AssertionError("L'API ne doit pas être appelée si le cache existe")

    monkeypatch.setattr(ingestion.requests, "get", fail_get)

    result = ingestion.fetch_fixture(12345)
    assert result == cached_payload


def test_fetch_fixture_calls_api_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    monkeypatch.setattr(ingestion, "require_api_football_key", lambda: "fake-key")

    responses = {
        "fixtures": _FakeResponse({"response": [{"id": 999}], "errors": []}),
        "fixtures/statistics": _FakeResponse({"response": [{"stat": 1}], "errors": []}),
        "fixtures/players": _FakeResponse({"response": [{"players": []}], "errors": []}),
        "fixtures/events": _FakeResponse({"response": [{"event": 1}], "errors": []}),
    }

    def fake_get(url, headers, params, timeout):
        for endpoint, resp in responses.items():
            if url.endswith(endpoint):
                return resp
        raise AssertionError(f"URL inattendue: {url}")

    monkeypatch.setattr(ingestion.requests, "get", fake_get)

    result = ingestion.fetch_fixture(999)

    assert result["fixture"] == {"id": 999}
    assert result["statistics"] == [{"stat": 1}]
    assert (tmp_path / "999.json").exists()


def test_fetch_fixture_raises_on_missing_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    monkeypatch.setattr(ingestion, "require_api_football_key", lambda: "fake-key")

    def fake_get(url, headers, params, timeout):
        return _FakeResponse({"response": [], "errors": []})

    monkeypatch.setattr(ingestion.requests, "get", fake_get)

    with pytest.raises(ingestion.ApiFootballError):
        ingestion.fetch_fixture(424242)


def test_fetch_fixture_raises_on_rate_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    monkeypatch.setattr(ingestion, "require_api_football_key", lambda: "fake-key")

    def fake_get(url, headers, params, timeout):
        return _FakeResponse({}, status_code=429, headers={"x-ratelimit-requests-remaining": "0"})

    monkeypatch.setattr(ingestion.requests, "get", fake_get)

    with pytest.raises(ingestion.RateLimitError):
        ingestion.fetch_fixture(1)


def test_fetch_fixture_resumes_after_partial_rate_limit(tmp_path, monkeypatch):
    """Si un des 4 appels échoue (429) en cours de route, les appels déjà
    réussis doivent rester en cache et ne pas être refaits au prochain essai.
    """
    monkeypatch.setattr(ingestion, "DATA_RAW_DIR", tmp_path)
    monkeypatch.setattr(ingestion, "require_api_football_key", lambda: "fake-key")

    call_log = []
    events_should_fail = True

    def fake_get(url, headers, params, timeout):
        if url.endswith("fixtures") and "id" in params:
            call_log.append("fixtures")
            return _FakeResponse({"response": [{"id": 555}], "errors": []})
        if url.endswith("fixtures/statistics"):
            call_log.append("statistics")
            return _FakeResponse({"response": [{"stat": 1}], "errors": []})
        if url.endswith("fixtures/players"):
            call_log.append("players")
            return _FakeResponse({"response": [{"players": []}], "errors": []})
        if url.endswith("fixtures/events"):
            call_log.append("events")
            if events_should_fail:
                return _FakeResponse(
                    {}, status_code=429, headers={"x-ratelimit-requests-remaining": "0"}
                )
            return _FakeResponse({"response": [{"event": 1}], "errors": []})
        raise AssertionError(f"URL inattendue: {url}")

    monkeypatch.setattr(ingestion.requests, "get", fake_get)

    with pytest.raises(ingestion.RateLimitError):
        ingestion.fetch_fixture(555)

    # les 3 premiers appels ont réussi et doivent être en cache sur disque
    cached = json.loads((tmp_path / "555.json").read_text(encoding="utf-8"))
    assert set(cached.keys()) == {"fixture_id", "fixture", "statistics", "players"}
    assert call_log == ["fixtures", "statistics", "players", "events"]

    # deuxième essai (quota reconstitué) : seul "events" doit être rappelé
    call_log.clear()
    events_should_fail = False
    result = ingestion.fetch_fixture(555)

    assert call_log == ["events"]
    assert result["events"] == [{"event": 1}]
    assert result["fixture"] == {"id": 555}
