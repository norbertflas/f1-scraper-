"""Scraper oficjalnego kalendarza Formuły 1 (formula1.com).

Strona F1 jest renderowana po stronie klienta i chroniona anty-botem, więc
nie traktujemy jej jako źródła tożsamości wyścigów. Źródłem prawdy jest
kanoniczny kalendarz sezonu (``data_fallback``) – dzięki temu klucze wyścigów
są stabilne i zgodne z tym, do czego odwołują się scrapery torów/partnerów.

Gdy stronę uda się pobrać, wzbogacamy jedynie ``official_url`` poszczególnych
wyścigów (best effort). Niepowodzenie pobrania niczego nie psuje.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from .. import data_fallback
from ..models import Race, TicketOffer
from .base import BaseScraper

log = logging.getLogger("f1scraper.calendar")

SCHEDULE_URL = "https://www.formula1.com/en/racing/2026.html"


class F1CalendarScraper(BaseScraper):
    name = "Kalendarz F1 (oficjalny)"
    source_type = "calendar"

    def scrape(self) -> tuple[list[Race], list[TicketOffer]]:
        # Kanoniczny kalendarz = stabilna tożsamość wyścigów (klucze, nazwy).
        races = data_fallback.calendar_2026()
        html = self.fetcher.get(SCHEDULE_URL)
        if html:
            enriched = self._enrich_urls(races, html)
            log.info("Kalendarz F1: wzbogacono %d adresów na żywo", enriched)
        else:
            log.info("Kalendarz F1 niedostępny na żywo – używam kanonicznego.")
        return races, []

    def _enrich_urls(self, races: list[Race], html: str) -> int:
        """Best-effort: dopasuj linki ze strony do kanonicznych wyścigów.

        Dopasowanie po fragmencie kraju/miasta/nazwie GP w adresie linku.
        Brak dopasowania = po prostu zostaje kanoniczny ``official_url``.
        """
        soup = BeautifulSoup(html, "lxml")
        count = 0
        for link in soup.select('a[href*="/racing/2026/"]'):
            href = self._absolute(link.get("href", ""))
            slug = href.lower()
            for race in races:
                if race.official_url and "/racing/2026/" in race.official_url:
                    # już wzbogacony konkretnym adresem – pomiń
                    continue
                if self._matches(race, slug):
                    race.official_url = href
                    count += 1
                    break
        return count

    @staticmethod
    def _matches(race: Race, slug: str) -> bool:
        tokens = {
            _norm(race.country),
            _norm(race.city),
            _norm(race.name.split(" Grand Prix")[0]),
        }
        return any(tok and tok in slug for tok in tokens)

    @staticmethod
    def _absolute(href: str) -> str:
        if href.startswith("http"):
            return href
        return "https://www.formula1.com" + href


def _norm(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum())
