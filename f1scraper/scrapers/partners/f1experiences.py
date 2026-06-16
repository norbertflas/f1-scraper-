"""Przykładowy partner: oficjalny program doświadczeń premium."""

from __future__ import annotations

from .base_partner import PartnerScraper


class F1ExperiencesScraper(PartnerScraper):
    name = "F1 Experiences (partner)"
    base_url = "https://f1experiences.com/"
    currency = "EUR"
    price_multiplier = 1.35  # pakiety premium są droższe
    covered_races = [
        "Monaco Grand Prix",
        "Italian Grand Prix",
        "Singapore Grand Prix",
        "United States Grand Prix",
        "Abu Dhabi Grand Prix",
    ]
