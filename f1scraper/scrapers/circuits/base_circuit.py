"""Bazowy scraper toru wyścigowego.

Implementuje wspólny przepływ: pobierz stronę biletową → sparsuj oferty →
w razie niepowodzenia użyj danych zapasowych dla danego wyścigu.

Konkretny tor podaje metadane (nazwa, URL, waluta) i może nadpisać ``_parse``
własnymi selektorami. Domyślny ``_parse`` zwraca pustą listę (czyli wpada
fallback), bo każdy tor ma inny układ strony.
"""

from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from ... import data_fallback
from ...models import Race, TicketOffer
from ..base import BaseScraper

log = logging.getLogger("f1scraper.circuit")


class CircuitScraper(BaseScraper):
    source_type = "circuit"

    #: Nazwa wyścigu zgodna z kalendarzem (Race.name), do powiązania ofert.
    race_name: str = ""
    #: Adres strony ze sprzedażą biletów na tym torze.
    tickets_url: str = ""
    #: Waluta, w której tor podaje ceny.
    currency: str = "EUR"
    #: Mnożnik ceny dla danych zapasowych (1.0 = ceny "oficjalne" toru).
    price_multiplier: float = 1.0

    def scrape(self) -> tuple[list[Race], list[TicketOffer]]:
        offers: list[TicketOffer] = []
        html = self.tickets_url and self.fetcher.get(self.tickets_url)
        if html:
            offers = self._parse(html)
            if offers:
                log.info("%s: %d ofert na żywo", self.name, len(offers))
        if not offers:
            offers = self._fallback_offers()
        return [], offers

    def _fallback_offers(self) -> list[TicketOffer]:
        return data_fallback.sample_offers_for(
            race_name=self.race_name,
            source_type=self.source_type,
            source_name=self.name,
            base_currency=self.currency,
            base_url=self.tickets_url,
            price_multiplier=self.price_multiplier,
        )

    # Domyślnie brak parsowania na żywo – nadpisz w konkretnym torze.
    def _parse(self, html: str) -> list[TicketOffer]:  # noqa: ARG002
        return []

    # Pomocnik dla podklas: powiązanie oferty z wyścigiem po nazwie.
    def _race_key(self) -> str:
        race = data_fallback.race_by_name(self.race_name)
        return race.key if race else ""

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")
