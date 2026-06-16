"""Bazowy scraper autoryzowanego partnera biletowego."""

from __future__ import annotations

import logging

from ... import data_fallback
from ...models import Race, TicketOffer
from ..base import BaseScraper

log = logging.getLogger("f1scraper.partner")


class PartnerScraper(BaseScraper):
    source_type = "partner"

    #: Adres bazowy partnera (strona z listą wyścigów).
    base_url: str = ""
    #: Waluta cen partnera.
    currency: str = "EUR"
    #: Mnożnik ceny względem cen toru (partnerzy zwykle drożsi).
    price_multiplier: float = 1.15
    #: Lista nazw wyścigów (Race.name) obsługiwanych przez partnera.
    covered_races: list[str] = []
    #: Sezony, dla których partner sprzedaje bilety (puste = wszystkie).
    seasons: list[int] = []

    def scrape(self) -> tuple[list[Race], list[TicketOffer]]:
        offers: list[TicketOffer] = []
        html = self.base_url and self.fetcher.get(self.base_url)
        if html:
            offers = self._parse(html)
            if offers:
                log.info("%s: %d ofert na żywo", self.name, len(offers))
        if not offers:
            offers = self._fallback_offers()
        return [], offers

    def _fallback_offers(self) -> list[TicketOffer]:
        offers: list[TicketOffer] = []
        for race_name in self.covered_races:
            for race in data_fallback.find_races(race_name, self.seasons or None):
                offers.extend(
                    data_fallback.sample_offers_for(
                        race=race,
                        source_type=self.source_type,
                        source_name=self.name,
                        base_currency=self.currency,
                        base_url=self.base_url,
                        price_multiplier=self.price_multiplier,
                    )
                )
        return offers

    def _parse(self, html: str) -> list[TicketOffer]:  # noqa: ARG002
        # Domyślnie brak parsowania na żywo – wymaga zgody/regulaminu partnera.
        return []
