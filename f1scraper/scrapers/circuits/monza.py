"""Scraper toru Monza (Italian Grand Prix)."""

from __future__ import annotations

from ...models import TicketOffer
from .base_circuit import CircuitScraper


class MonzaScraper(CircuitScraper):
    name = "Monza (oficjalna)"
    race_name = "Italian Grand Prix"
    tickets_url = "https://www.monzanet.it/en/tickets/"
    currency = "EUR"
    price_multiplier = 1.0

    def _parse(self, html: str) -> list[TicketOffer]:
        """Przykład parsowania na żywo.

        Układ HTML strony toru zmienia się co sezon, więc traktujemy to jako
        szablon do dostosowania. Gdy selektory nic nie znajdą – zwracamy []
        i bazowa klasa użyje danych zapasowych.
        """
        soup = self._soup(html)
        offers: list[TicketOffer] = []
        race_key = self._race_key()
        for card in soup.select(".ticket-card, .product-item"):
            name_el = card.select_one(".title, h3, .product-title")
            price_el = card.select_one(".price, .amount")
            if not (name_el and price_el):
                continue
            price = _parse_price(price_el.get_text())
            if price is None:
                continue
            offers.append(
                TicketOffer(
                    race_key=race_key,
                    source_type=self.source_type,
                    source_name=self.name,
                    grandstand=name_el.get_text(strip=True),
                    category="Weekend 3-dniowy",
                    price=price,
                    currency=self.currency,
                    buy_url=self.tickets_url,
                )
            )
        return offers


def _parse_price(text: str) -> float | None:
    digits = "".join(c for c in text if c.isdigit() or c in ".,")
    digits = digits.replace(".", "").replace(",", ".") if "," in digits else digits
    try:
        return float(digits)
    except ValueError:
        return None
