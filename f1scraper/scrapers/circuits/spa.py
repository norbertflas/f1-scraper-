"""Scraper toru Spa-Francorchamps (Belgian Grand Prix)."""

from __future__ import annotations

from .base_circuit import CircuitScraper


class SpaScraper(CircuitScraper):
    name = "Spa-Francorchamps (oficjalna)"
    race_name = "Belgian Grand Prix"
    tickets_url = "https://www.spa-francorchamps.be/en/tickets"
    currency = "EUR"
    price_multiplier = 1.0
