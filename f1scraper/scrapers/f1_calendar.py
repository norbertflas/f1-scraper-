"""Scraper oficjalnego kalendarza Formuły 1 (formula1.com).

Strona F1 jest renderowana po stronie klienta i chroniona anty-botem, więc
parsowanie HTML jest "best effort". Gdy się nie powiedzie, używamy wbudowanego
kalendarza z ``data_fallback``.
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
        html = self.fetcher.get(SCHEDULE_URL)
        if html:
            races = self._parse(html)
            if races:
                return races, []
            log.info("Parsowanie kalendarza F1 nie dało wyników – fallback.")
        else:
            log.info("Nie udało się pobrać kalendarza F1 – fallback.")
        # Fallback: wbudowany kalendarz sezonu.
        return data_fallback.calendar_2026(), []

    def _parse(self, html: str) -> list[Race]:
        """Best-effort parsowanie listy wyścigów.

        Selektory celowo są ostrożne – jeśli układ strony się zmieni, po
        prostu zwracamy pustą listę i wpada fallback.
        """
        soup = BeautifulSoup(html, "lxml")
        races: list[Race] = []
        # F1 oznacza karty wyścigów linkami zawierającymi /racing/2026/<kraj>.
        seen: set[str] = set()
        for idx, link in enumerate(soup.select('a[href*="/racing/2026/"]'), start=1):
            href = link.get("href", "")
            if href in seen:
                continue
            text = link.get_text(" ", strip=True)
            if not text:
                continue
            seen.add(href)
            name = text.split("\n")[0][:80]
            races.append(
                Race(
                    round=len(races) + 1,
                    name=name,
                    circuit="",
                    country="",
                    city="",
                    official_url=self._absolute(href),
                )
            )
        return races

    @staticmethod
    def _absolute(href: str) -> str:
        if href.startswith("http"):
            return href
        return "https://www.formula1.com" + href
