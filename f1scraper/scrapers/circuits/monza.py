"""Scraper toru Monza (Italian Grand Prix).

Strategia parsowania (od najpewniejszej):
  1. dane strukturalne schema.org (JSON-LD) – jeśli strona je publikuje,
  2. karty produktów/biletów w HTML – odporne selektory + heurystyki.

Gdy nic nie zadziała, bazowa klasa użyje danych zapasowych.
"""

from __future__ import annotations

import logging

from ...models import TicketOffer
from ...parsing import (
    detect_currency,
    guess_covered,
    guess_seat_quality,
    parse_price,
)
from .base_circuit import CircuitScraper

log = logging.getLogger("f1scraper.circuit.monza")

# Selektory kandydujące – strona zmienia się co sezon, więc próbujemy kilku.
_CARD_SELECTORS = ".ticket-card, .product-item, .product, li.ticket, .card--ticket"
_NAME_SELECTORS = ".title, .product-title, .ticket__title, h3, h4, .name"
_PRICE_SELECTORS = ".price, .amount, .product-price, .ticket__price, [data-price]"
_AVAIL_SELECTORS = ".availability, .stock, .badge, .ticket__status"


class MonzaScraper(CircuitScraper):
    name = "Monza (oficjalna)"
    race_name = "Italian Grand Prix"
    tickets_url = "https://www.monzanet.it/en/tickets/"
    currency = "EUR"
    price_multiplier = 1.0

    def _parse(self, html: str) -> list[TicketOffer]:
        # 1) Najpierw dane strukturalne (najbardziej niezawodne).
        offers = self._offers_from_jsonld(html)
        if offers:
            log.info("Monza: %d ofert z JSON-LD", len(offers))
            return offers
        # 2) Fallback: parsowanie kart HTML.
        return self._parse_cards(html)

    def _parse_cards(self, html: str) -> list[TicketOffer]:
        soup = self._soup(html)
        race_key = self._race_key()
        offers: list[TicketOffer] = []
        for card in soup.select(_CARD_SELECTORS):
            name_el = card.select_one(_NAME_SELECTORS)
            price_el = card.select_one(_PRICE_SELECTORS)
            if not (name_el and price_el):
                continue
            price_text = price_el.get("data-price") or price_el.get_text()
            price = parse_price(price_text)
            if price is None:
                continue
            name = name_el.get_text(strip=True)
            avail_el = card.select_one(_AVAIL_SELECTORS)
            availability = _avail_from_text(avail_el.get_text() if avail_el else "")
            link = card.select_one("a[href]")
            buy_url = link["href"] if link else self.tickets_url

            offers.append(
                TicketOffer(
                    race_key=race_key,
                    source_type=self.source_type,
                    source_name=self.name,
                    grandstand=name,
                    category="Weekend 3-dniowy",
                    price=price,
                    currency=detect_currency(price_text, self.currency),
                    seat_quality=guess_seat_quality(name),
                    covered=guess_covered(name),
                    availability=availability,
                    buy_url=_absolute(buy_url),
                )
            )
        if offers:
            log.info("Monza: %d ofert z kart HTML", len(offers))
        return offers


def _avail_from_text(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("sold out", "esaurito", "wyprzed")):
        return "wyprzedane"
    if any(k in low for k in ("last", "ultimi", "few", "ostatni")):
        return "ostatnie"
    return "dostępne"


def _absolute(href: str) -> str:
    if href.startswith("http"):
        return href
    return "https://www.monzanet.it" + ("" if href.startswith("/") else "/") + href
