"""Scraper toru Silverstone (British Grand Prix)."""

from __future__ import annotations

from .base_circuit import CircuitScraper


class SilverstoneScraper(CircuitScraper):
    name = "Silverstone (oficjalna)"
    race_name = "British Grand Prix"
    tickets_url = "https://www.silverstone.co.uk/events/formula-1"
    currency = "GBP"
    price_multiplier = 1.0
