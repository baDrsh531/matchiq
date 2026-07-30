"""Revue de presse d'un match : contexte EXTERNE, cité, jamais injecté dans le score.

Adapté du pont de recherche généraliste (searche_bridge.py) mais réduit et
verrouillé pour l'usage de MatchIQ :

  * on garde ce qui a fait ses preuves : GDELT (actualités mondiales en temps
    réel, sans clé), un cache TTL, un disjoncteur (circuit breaker), et le
    contournement du proxy système (trust_env) ;
  * on jette tout le reste du pont d'origine (Flask autonome, images, documents,
    ZIP) qui n'a aucun sens ici — et qui, exposé sans authentification, serait un
    risque.

Quatre règles NON négociables, cohérentes avec l'identité du projet :
  1. le mode démo coupe le réseau AVANT toute I/O (même contrat que l'API-Football
     et le LLM) — une instance publique « sans appel sortant » le reste ;
  2. la sortie part dans un champ SÉPARÉ (`external_context`), citée (URL + date) ;
     elle n'entre JAMAIS dans le moteur de score ni dans le prompt factuel ;
  3. un badge de confiance distinct : « donnée officielle » (API, calculée) vs
     « contexte presse » (externe, non vérifié) ;
  4. la requête est construite à partir du match (équipes + compétition).
"""
from __future__ import annotations

import html as _html
import logging
import re
import threading
import time
from datetime import datetime
from urllib.parse import urlparse

import requests

from config import DEMO_MODE

logger = logging.getLogger("matchiq.press")

CONFIDENCE = "external_unverified"   # badge : contexte externe, non vérifié
_CACHE_TTL = 900                     # 15 min : l'actu d'un match passé ne bouge plus
_TIMEOUT = 12.0
_CB_THRESHOLD = 3                    # échecs consécutifs avant mise en pause
_CB_COOLDOWN = 120

# Réseaux sociaux / agrégateurs : bruit pour une revue de presse.
_BAD_DOMAINS = {"pinterest.com", "facebook.com", "instagram.com", "tiktok.com",
                "twitter.com", "x.com", "youtube.com"}

_SESSION = requests.Session()
# Beaucoup de machines ont un proxy système mal configuré qui casse toute requête
# sortante ; le pont a besoin d'un accès direct (comportement repris de l'original).
import os as _os  # noqa: E402
_SESSION.trust_env = _os.environ.get("RESPECT_PROXY", "").lower() in ("1", "true", "yes")


class PressUnavailableError(RuntimeError):
    """Revue de presse indisponible (mode démo, disjoncteur ouvert, réseau)."""


# ── Cache TTL + circuit breaker (repris, en plus compact) ───────────────────
_cache: dict[str, tuple[float, list]] = {}
_fail_count = 0
_cooldown_until = 0.0
_lock = threading.Lock()


def _cache_get(key: str):
    with _lock:
        hit = _cache.get(key)
        if hit and (time.time() - hit[0]) < _CACHE_TTL:
            return hit[1]
    return None


def _cache_set(key: str, value: list):
    with _lock:
        _cache[key] = (time.time(), value)


def _breaker_open() -> bool:
    with _lock:
        return time.time() < _cooldown_until


def _record(ok: bool):
    global _fail_count, _cooldown_until
    with _lock:
        if ok:
            _fail_count = 0
        else:
            _fail_count += 1
            if _fail_count >= _CB_THRESHOLD:
                _cooldown_until = time.time() + _CB_COOLDOWN
                logger.warning("[press] disjoncteur ouvert (%ss)", _CB_COOLDOWN)


def _clean(text) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    return re.sub(r"\s+", " ", _html.unescape(text)).strip()


def _is_bad(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        host = host[4:] if host.startswith("www.") else host
        return any(host == b or host.endswith("." + b) for b in _BAD_DOMAINS)
    except Exception:
        return False


def _search_gdelt(query: str, limit: int) -> list[dict]:
    """GDELT Doc 2.0 : articles récents du monde entier, sans clé."""
    resp = _SESSION.get(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={"query": query, "mode": "ArtList", "format": "json",
                "maxrecords": min(max(limit, 1), 25), "sort": "DateDesc"},
        headers={"User-Agent": "MatchIQ/1.0 (press context)"},
        timeout=_TIMEOUT,
    )
    data = resp.json() if resp.text.strip().startswith("{") else {}
    out = []
    for a in data.get("articles", []):
        url = a.get("url", "")
        if not url or _is_bad(url):
            continue
        out.append({
            "title": _clean(a.get("title")) or url,
            "url": url,
            "domain": a.get("domain", ""),
            "date": a.get("seendate", ""),
            "source": "GDELT",
        })
    return out


def build_query(home: str, away: str, league: str | None = None) -> str:
    # Les deux équipes en phrases exactes ciblent les articles du match précis.
    # (On évite d'ajouter « football » : sur GDELT, empiler les contraintes vide
    # souvent le résultat pour un match pourtant couvert.)
    return " ".join(f'"{t}"' for t in (home, away) if t).strip()


def match_press(home: str, away: str, league: str | None = None, limit: int = 5) -> dict:
    """Revue de presse d'une affiche. Renvoie un bloc CLAIREMENT séparé et cité :
        {confidence, disclaimer, query, generated_at, sources:[...]}

    Lève PressUnavailableError en mode démo (aucun appel sortant) ou si le service
    externe est indisponible."""
    if DEMO_MODE:
        raise PressUnavailableError(
            "Mode démo : la revue de presse (appel externe) est désactivée sur "
            "cette instance publique."
        )
    if _breaker_open():
        raise PressUnavailableError("Service de presse temporairement indisponible (disjoncteur).")

    query = build_query(home, away, league)
    cached = _cache_get(query)
    if cached is not None:
        sources = cached
    else:
        try:
            sources = _search_gdelt(query, limit)
            _record(True)
            _cache_set(query, sources)
        except requests.RequestException as exc:
            _record(False)
            raise PressUnavailableError(f"Échec réseau de la revue de presse : {exc}") from exc

    return {
        "confidence": CONFIDENCE,
        "disclaimer": (
            "Contexte externe non vérifié — issu de la presse en ligne, cité pour "
            "information. N'entre jamais dans le calcul des scores ni dans le rapport factuel."
        ),
        "query": query,
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "sources": sources[:limit],
    }
