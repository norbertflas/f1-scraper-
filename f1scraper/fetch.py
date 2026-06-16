"""Uprzejmy klient HTTP do scrapowania.

Zasady "dobrego obywatela sieci":
  * respektujemy robots.txt (chyba że jawnie wyłączone),
  * ograniczamy tempo zapytań do jednej domeny (rate limit),
  * cache'ujemy odpowiedzi na dysku, żeby nie dobijać serwerów,
  * przedstawiamy się czytelnym User-Agentem.

Każdy błąd sieci jest "miękki" – zwracamy None, a scraper może wtedy
skorzystać z danych zapasowych (fallback).
"""

from __future__ import annotations

import hashlib
import logging
import time
import urllib.robotparser
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

log = logging.getLogger("f1scraper.fetch")

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; F1TicketScraper/0.1; "
    "+https://github.com/norbertflas/f1-scraper-)"
)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "http_cache"


class PoliteFetcher:
    """Pobiera strony z poszanowaniem robots.txt, rate limitu i cache."""

    def __init__(
        self,
        user_agent: str = DEFAULT_UA,
        min_interval: float = 1.5,
        timeout: float = 12.0,
        cache_ttl: float = 6 * 3600,
        respect_robots: bool = True,
        cache_dir: Path = CACHE_DIR,
    ) -> None:
        self.user_agent = user_agent
        self.min_interval = min_interval
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.respect_robots = respect_robots
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "pl,en;q=0.8",
            }
        )
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser] = {}

    # -- robots.txt -----------------------------------------------------
    def _robots_for(self, url: str) -> urllib.robotparser.RobotFileParser:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
            except Exception as exc:  # pragma: no cover - sieć bywa zawodna
                log.debug("Nie udało się wczytać robots.txt dla %s: %s", host, exc)
                rp = urllib.robotparser.RobotFileParser()
                rp.parse([])  # brak reguł => domyślnie dozwolone
            self._robots[host] = rp
        return self._robots[host]

    def allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        try:
            return self._robots_for(url).can_fetch(self.user_agent, url)
        except Exception:
            return True

    # -- rate limiting --------------------------------------------------
    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request.get(host, 0.0)
        wait = self.min_interval - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_request[host] = time.monotonic()

    # -- cache ----------------------------------------------------------
    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.html"

    def _read_cache(self, url: str) -> Optional[str]:
        path = self._cache_path(url)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.cache_ttl:
            return None
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _write_cache(self, url: str, text: str) -> None:
        try:
            self._cache_path(url).write_text(text, encoding="utf-8")
        except OSError as exc:  # pragma: no cover
            log.debug("Nie udało się zapisać cache dla %s: %s", url, exc)

    # -- API ------------------------------------------------------------
    def get(self, url: str, use_cache: bool = True) -> Optional[str]:
        """Zwraca treść strony lub None przy błędzie/zablokowaniu."""
        if use_cache:
            cached = self._read_cache(url)
            if cached is not None:
                log.debug("CACHE HIT %s", url)
                return cached

        if not self.allowed(url):
            log.warning("robots.txt blokuje pobieranie %s – pomijam", url)
            return None

        self._throttle(url)
        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            log.warning("Błąd sieci przy %s: %s", url, exc)
            return None

        if resp.status_code != 200:
            log.warning("HTTP %s przy %s", resp.status_code, url)
            return None

        text = resp.text
        if use_cache:
            self._write_cache(url, text)
        return text
