"""Scraper toru Monaco (Monaco Grand Prix) – oficjalna sprzedaż ACM.

Monaco to weekend 4-dniowy (czwartek–niedziela) – kategoria „Weekend 4-dniowy"
i wyższe ceny wynikają z ``weekend_days=4`` w kalendarzu. Dostępny też dodatek
Pit Lane Walk.
"""

from __future__ import annotations

from .base_circuit import CircuitScraper


class MonacoScraper(CircuitScraper):
    name = "Monaco / ACM (oficjalna)"
    race_name = "Monaco Grand Prix"
    tickets_url = "https://www.acm.mc/en/tickets/"
    currency = "EUR"
    price_multiplier = 1.0
