"""Przykładowy partner: globalny reseller (oferta na wiele wyścigów)."""

from __future__ import annotations

from .base_partner import PartnerScraper


class GooTicketsScraper(PartnerScraper):
    name = "GooTickets (partner)"
    base_url = "https://www.gootickets.com/en/formula-1"
    currency = "EUR"
    price_multiplier = 1.18
    covered_races = [
        "Monaco Grand Prix",
        "Italian Grand Prix",
        "Belgian Grand Prix",
        "British Grand Prix",
        "Dutch Grand Prix",
        "Las Vegas Grand Prix",
    ]
