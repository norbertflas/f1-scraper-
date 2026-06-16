"""Scraper toru Yas Marina (Abu Dhabi Grand Prix) – finał sezonu."""

from __future__ import annotations

from .base_circuit import CircuitScraper


class AbuDhabiScraper(CircuitScraper):
    name = "Yas Marina / Abu Dhabi (oficjalna)"
    race_name = "Abu Dhabi Grand Prix"
    tickets_url = "https://www.yasmarinacircuit.com/en/f1"
    currency = "AED"
    price_multiplier = 1.0
