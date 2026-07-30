"""Monitoring FinOps/MLOps du LLM : coût, tokens, latence, taux de succès.

Le client LLM étant un point de passage unique, on y enregistre une ligne par
appel (append-only JSONL, `data/llm_metrics.jsonl`). Un endpoint agrège ensuite
ces lignes en tableau de bord — combien d'appels, combien de tokens, combien ça
a coûté, quelle latence, quel taux d'échec, ventilé par modèle.

Le coût est estimé à partir d'une grille de tarifs (USD / million de tokens).
Un backend local (vLLM/llama.cpp) est gratuit : coût 0, mais on suit quand même
tokens et latence (le « FinOps » d'un modèle local, c'est le temps GPU)."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from config import DATA_DIR

METRICS_PATH: Path = DATA_DIR / "llm_metrics.jsonl"
_lock = threading.Lock()

# Tarifs indicatifs en USD par MILLION de tokens (entrée, sortie). Un modèle
# absent de la grille (ex. modèle local) est facturé 0. À ajuster selon le plan.
PRICING: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash": (0.075, 0.30),
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-2.5-pro": (1.25, 5.00),
}


def _price(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    inp, out = PRICING.get(model, (0.0, 0.0))
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000.0


def record_call(provider: str, model: str, prompt_tokens: int, completion_tokens: int,
                latency_ms: float, ok: bool, error: str | None = None,
                estimated: bool = False) -> None:
    """Ajoute une ligne de métrique (jamais bloquant pour l'appelant : toute
    erreur d'écriture est silencieuse — le monitoring ne doit pas casser l'app)."""
    entry = {
        "ts": time.time(),
        "provider": provider,
        "model": model,
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "latency_ms": round(latency_ms, 1),
        "cost_usd": round(_price(model, prompt_tokens or 0, completion_tokens or 0), 6),
        "ok": bool(ok),
        "estimated_tokens": bool(estimated),
    }
    if error:
        entry["error"] = error[:200]
    try:
        with _lock:
            METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with METRICS_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _read() -> list[dict]:
    if not METRICS_PATH.exists():
        return []
    rows = []
    with METRICS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def summary(recent: int = 20) -> dict:
    """Agrège toutes les métriques enregistrées en un tableau de bord."""
    rows = _read()
    if not rows:
        return {"calls": 0, "ok": 0, "failed": 0, "success_rate": None,
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                "cost_usd": 0.0, "avg_latency_ms": None, "by_model": [], "recent": []}

    ok = sum(1 for r in rows if r.get("ok"))
    pt = sum(r.get("prompt_tokens", 0) for r in rows)
    ct = sum(r.get("completion_tokens", 0) for r in rows)
    cost = sum(r.get("cost_usd", 0.0) for r in rows)
    lat = [r.get("latency_ms") for r in rows if r.get("latency_ms") is not None]

    by_model: dict[str, dict] = {}
    for r in rows:
        m = by_model.setdefault(r.get("model", "?"), {
            "model": r.get("model", "?"), "provider": r.get("provider", "?"),
            "calls": 0, "tokens": 0, "cost_usd": 0.0, "_lat": []})
        m["calls"] += 1
        m["tokens"] += r.get("prompt_tokens", 0) + r.get("completion_tokens", 0)
        m["cost_usd"] += r.get("cost_usd", 0.0)
        if r.get("latency_ms") is not None:
            m["_lat"].append(r["latency_ms"])
    models = []
    for m in by_model.values():
        models.append({
            "model": m["model"], "provider": m["provider"], "calls": m["calls"],
            "tokens": m["tokens"], "cost_usd": round(m["cost_usd"], 6),
            "avg_latency_ms": round(sum(m["_lat"]) / len(m["_lat"]), 1) if m["_lat"] else None,
        })
    models.sort(key=lambda x: -x["calls"])

    return {
        "calls": len(rows),
        "ok": ok,
        "failed": len(rows) - ok,
        "success_rate": round(ok / len(rows), 3),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": pt + ct,
        "cost_usd": round(cost, 6),
        "avg_latency_ms": round(sum(lat) / len(lat), 1) if lat else None,
        "by_model": models,
        "recent": rows[-recent:][::-1],   # plus récent d'abord
    }
