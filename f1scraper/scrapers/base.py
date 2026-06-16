"""Bazowa klasa dla wszystkich scraperów."""

from __future__ import annotations

import abc
import logging
from typing import Iterable

from ..fetch import PoliteFetcher
from ..models import Race, TicketOffer

log = logging.getLogger("f1scraper.scraper")


class BaseScraper(abc.ABC):
    """Wspólny interfejs scrapera.

    Konkretny scraper implementuje ``scrape()`` i zwraca (wyścigi, oferty).
    Jeśli scrapowanie na żywo się nie powiedzie (403, brak sieci, zmiana
    HTML), powinien wywołać ``self.fallback()`` z danymi zapasowymi, żeby
    aplikacja nadal coś pokazała.
    """

    #: Czytelna nazwa źródła, np. "Monza (oficjalna)".
    name: str = "base"
    #: Typ źródła: "calendar" | "circuit" | "partner".
    source_type: str = "calendar"

    def __init__(self, fetcher: PoliteFetcher | None = None) -> None:
        self.fetcher = fetcher or PoliteFetcher()

    @abc.abstractmethod
    def scrape(self) -> tuple[list[Race], list[TicketOffer]]:
        """Zwraca listę wyścigów i ofert z tego źródła."""

    # Pomocnicze: bezpieczne uruchomienie z logowaniem błędów.
    def safe_scrape(self) -> tuple[list[Race], list[TicketOffer]]:
        try:
            races, offers = self.scrape()
            log.info(
                "%s: %d wyścigów, %d ofert", self.name, len(races), len(offers)
            )
            return list(races), list(offers)
        except Exception as exc:  # pragma: no cover - defensywnie
            log.error("%s: scrapowanie nieudane (%s)", self.name, exc)
            return [], []

    @staticmethod
    def fallback(
        races: Iterable[Race] = (), offers: Iterable[TicketOffer] = ()
    ) -> tuple[list[Race], list[TicketOffer]]:
        return list(races), list(offers)
