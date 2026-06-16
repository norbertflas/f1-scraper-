"""Testy silnika i modeli (działają offline, na danych zapasowych)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from f1scraper.engine import run_scrape  # noqa: E402
from f1scraper.models import TicketOffer  # noqa: E402


def test_run_scrape_produces_races_and_offers():
    result = run_scrape()
    assert len(result.races) >= 20  # pełny kalendarz sezonu
    assert len(result.offers) > 0
    # Każda oferta powinna wskazywać na istniejący wyścig.
    keys = {r.key for r in result.races}
    linked = [o for o in result.offers if o.race_key in keys]
    assert linked, "oferty nie są powiązane z wyścigami"


def test_value_score_prefers_cheaper_same_quality():
    cheap = TicketOffer(race_key="x", source_type="circuit", source_name="A",
                        grandstand="g", category="c", price=100, seat_quality=8)
    pricey = TicketOffer(race_key="x", source_type="circuit", source_name="B",
                         grandstand="g", category="c", price=400, seat_quality=8)
    assert cheap.value_score(4.0) > pricey.value_score(4.0)


def test_sold_out_has_zero_value():
    o = TicketOffer(race_key="x", source_type="circuit", source_name="A",
                    grandstand="g", category="c", price=100, seat_quality=9,
                    availability="wyprzedane")
    assert o.value_score(5.0) == 0.0


def test_currency_normalisation_to_eur():
    gbp = TicketOffer(race_key="x", source_type="circuit", source_name="A",
                      grandstand="g", category="c", price=100, currency="GBP")
    assert gbp.price_eur > 100  # GBP droższy niż EUR


def test_ranked_offers_respects_max_price():
    result = run_scrape()
    rows = result.ranked_offers(max_price_eur=150)
    assert rows, "powinny być jakieś tanie oferty"
    assert all(r["price_eur"] <= 150 for r in rows)


def test_best_per_race_unique_races():
    result = run_scrape()
    rows = result.best_per_race()
    keys = [r["race_key"] for r in rows]
    assert len(keys) == len(set(keys)), "duplikaty wyścigów w best_per_race"


def test_sort_by_price_ascending():
    result = run_scrape()
    rows = result.ranked_offers(sort_by="price")
    prices = [r["price_eur"] for r in rows]
    assert prices == sorted(prices)
