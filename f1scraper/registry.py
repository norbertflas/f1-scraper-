"""Rejestr wszystkich aktywnych scraperów.

Dodajesz nowe źródło? Dopisz jego klasę tutaj.
"""

from __future__ import annotations

from .scrapers.base import BaseScraper
from .scrapers.circuits.monza import MonzaScraper
from .scrapers.circuits.silverstone import SilverstoneScraper
from .scrapers.circuits.spa import SpaScraper
from .scrapers.f1_calendar import F1CalendarScraper
from .scrapers.partners.f1experiences import F1ExperiencesScraper
from .scrapers.partners.gootickets import GooTicketsScraper

# Kolejność ma znaczenie: kalendarz jako pierwszy (dostarcza listę wyścigów).
SCRAPER_CLASSES: list[type[BaseScraper]] = [
    F1CalendarScraper,
    MonzaScraper,
    SilverstoneScraper,
    SpaScraper,
    GooTicketsScraper,
    F1ExperiencesScraper,
]


def build_scrapers(fetcher=None) -> list[BaseScraper]:
    return [cls(fetcher=fetcher) for cls in SCRAPER_CLASSES]
