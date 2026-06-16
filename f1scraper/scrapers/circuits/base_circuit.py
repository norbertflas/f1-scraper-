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
from ...parsing import (
    extract_jsonld_offers,
    guess_covered,
    guess_seat_quality,
)
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
    #: Sezony, dla których generujemy oferty (puste = wszystkie z kalendarza).
    seasons: list[int] = []

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
        offers: list[TicketOffer] = []
        for race in data_fallback.find_races(self.race_name, self.seasons or None):
            offers.extend(
                data_fallback.sample_offers_for(
                    race=race,
                    source_type=self.source_type,
                    source_name=self.name,
                    base_currency=self.currency,
                    base_url=self.tickets_url,
                    price_multiplier=self.price_multiplier,
                )
            )
        return offers

    def _parse(self, html: str) -> list[TicketOffer]:
        """Domyślnie próbuje danych strukturalnych schema.org (JSON-LD).

        Wiele serwisów biletowych publikuje oferty jako Event/Product z polem
        ``offers``. Jeśli ich nie ma, zwracamy [] i wpada fallback. Konkretny
        tor może nadpisać tę metodę własnymi selektorami HTML (patrz Monza).
        """
        return self._offers_from_jsonld(html)

    def _offers_from_jsonld(self, html: str) -> list[TicketOffer]:
        race_key = self._race_key()
        offers: list[TicketOffer] = []
        for item in extract_jsonld_offers(html):
            offers.append(
                TicketOffer(
                    race_key=race_key,
                    source_type=self.source_type,
                    source_name=self.name,
                    grandstand=item["name"],
                    category="Weekend 3-dniowy",
                    price=item["price"],
                    currency=item["currency"] or self.currency,
                    seat_quality=guess_seat_quality(item["name"]),
                    covered=guess_covered(item["name"]),
                    availability=item["availability"],
                    buy_url=item["url"] or self.tickets_url,
                )
            )
        return offers

    # Pomocnik dla podklas: powiązanie oferty z wyścigiem po nazwie.
    # Dla parsowania na żywo bierzemy najbliższy sezon (live = bieżąca sprzedaż).
    def _race_key(self) -> str:
        season = min(self.seasons) if self.seasons else None
        race = data_fallback.race_by_name(self.race_name, season)
        return race.key if race else ""

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")
