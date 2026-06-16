"""Testy parsowania cen, JSON-LD i scrapera Monzy (offline, na fixture'ach)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest  # noqa: E402

from f1scraper.parsing import (  # noqa: E402
    detect_currency,
    extract_jsonld_offers,
    guess_seat_quality,
    parse_price,
)
from f1scraper.scrapers.circuits.monza import MonzaScraper  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("1.234,50 €", 1234.50),
    ("1,234.50", 1234.50),
    ("£295", 295.0),
    ("€ 89", 89.0),
    ("od 49,99 zł", 49.99),
    ("2 500", 2500.0),
    ("brak ceny", None),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_detect_currency():
    assert detect_currency("£295") == "GBP"
    assert detect_currency("99 zł") == "PLN"
    assert detect_currency("brak symbolu", default="USD") == "USD"


def test_guess_seat_quality_ranks_premium_above_ga():
    assert guess_seat_quality("Premium Grandstand Start/Finish") > guess_seat_quality("General Admission")


JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "Italian Grand Prix",
  "offers": [
    {"@type": "Offer", "name": "Tribune Central Premium", "price": "690",
     "priceCurrency": "EUR", "availability": "https://schema.org/InStock",
     "url": "https://example.com/buy/central"},
    {"@type": "Offer", "name": "General Admission", "price": "110.00",
     "priceCurrency": "EUR", "availability": "https://schema.org/SoldOut",
     "url": "https://example.com/buy/ga"}
  ]
}
</script>
</head><body></body></html>
"""


def test_extract_jsonld_offers():
    offers = extract_jsonld_offers(JSONLD_HTML)
    assert len(offers) == 2
    central = next(o for o in offers if "Central" in o["name"])
    assert central["price"] == 690.0
    assert central["currency"] == "EUR"
    assert central["availability"] == "dostępne"
    ga = next(o for o in offers if o["name"] == "General Admission")
    assert ga["availability"] == "wyprzedane"


def test_monza_parses_jsonld():
    scraper = MonzaScraper()
    offers = scraper._parse(JSONLD_HTML)
    assert len(offers) == 2
    premium = next(o for o in offers if "Central" in o.grandstand)
    assert premium.seat_quality >= 8  # heurystyka: premium/central = wysoka jakość
    assert premium.price == 690.0


CARDS_HTML = """
<html><body>
<div class="product-item">
  <h3 class="product-title">Main Grandstand Start/Finish</h3>
  <span class="price">€ 470,00</span>
  <span class="availability">Last tickets</span>
  <a href="/en/tickets/main">Buy</a>
</div>
<div class="product-item">
  <h3 class="product-title">Prato (General Admission)</h3>
  <span class="price">€ 110</span>
  <a href="https://www.monzanet.it/en/tickets/prato">Buy</a>
</div>
</body></html>
"""


def test_monza_parses_html_cards_when_no_jsonld():
    scraper = MonzaScraper()
    offers = scraper._parse(CARDS_HTML)
    assert len(offers) == 2
    main = next(o for o in offers if "Main" in o.grandstand)
    assert main.price == 470.0
    assert main.availability == "ostatnie"
    assert main.buy_url == "https://www.monzanet.it/en/tickets/main"
    ga = next(o for o in offers if "Prato" in o.grandstand)
    assert ga.seat_quality <= 4  # GA = niska jakość
