"""Testy silnika i modeli (działają offline, na danych zapasowych)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from f1scraper.engine import run_scrape  # noqa: E402
from f1scraper.models import TicketOffer  # noqa: E402
from f1scraper.scrapers.f1_calendar import F1CalendarScraper  # noqa: E402


class _FakeFetcher:
    """Zwraca podany HTML dla każdego URL-a (symuluje sieć na żywo)."""

    def __init__(self, html):
        self.html = html

    def get(self, url, use_cache=True):
        return self.html


def test_run_scrape_produces_races_and_offers():
    result = run_scrape(offline=True)
    assert len(result.races) >= 20  # pełny kalendarz sezonu
    assert len(result.offers) > 0
    # Każda oferta powinna wskazywać na istniejący wyścig.
    keys = {r.key for r in result.races}
    linked = [o for o in result.offers if o.race_key in keys]
    assert linked, "oferty nie są powiązane z wyścigami"


def test_calendar_keys_stable_even_with_live_html():
    # Regresja: parsowanie live nie może zmieniać tożsamości (kluczy) wyścigów,
    # bo wtedy oferty torów/partnerów przestają się z nimi łączyć.
    live_html = """
    <html><body>
      <a href="/en/racing/2026/italy.html">Italy Monza</a>
      <a href="/en/racing/2026/monaco.html">Monaco</a>
    </body></html>
    """
    scraper = F1CalendarScraper(fetcher=_FakeFetcher(live_html))
    races, _ = scraper.scrape()
    keys = {r.key for r in races}
    assert "2026-italian-grand-prix" in keys
    assert "2026-monaco-grand-prix" in keys
    assert len(races) >= 40  # dwa sezony
    # URL wzbogacony z linku na żywo (2026).
    italy = next(r for r in races if r.key == "2026-italian-grand-prix")
    assert italy.official_url.endswith("/racing/2026/italy.html")


def test_2027_calendar_present_with_monaco_4day_and_abu_dhabi_last():
    result = run_scrape(offline=True)
    races_2027 = [r for r in result.races if r.season == 2027]
    assert len(races_2027) >= 20
    monaco = next(r for r in races_2027 if r.name == "Monaco Grand Prix")
    assert monaco.weekend_days == 4
    # Abu Dhabi to ostatni wyścig sezonu.
    last = max(races_2027, key=lambda r: r.round)
    assert last.name == "Abu Dhabi Grand Prix"


def test_monaco_2027_has_4day_grandstand_and_pitlane():
    result = run_scrape(offline=True)
    rows = result.ranked_offers(season=2027, country="Monaco")
    cats = {r["category"] for r in rows}
    assert any("4-dniowy" in c for c in cats), "Monaco 2027 powinno mieć bilet 4-dniowy"
    assert any("Doświadczenie" in c for c in cats), "powinien być Pit Lane Walk"
    # Najtańsza trybuna 4-dniowa (z wykluczeniem GA przez jakość >= 5).
    grandstands = result.ranked_offers(
        season=2027, country="Monaco", category_contains="4-dniowy",
        min_seat_quality=5, sort_by="price",
    )
    assert grandstands
    assert grandstands[0]["price_eur"] <= grandstands[-1]["price_eur"]


def test_region_filter():
    result = run_scrape(offline=True)
    rows = result.ranked_offers(region="Europa")
    assert rows
    assert all(r["region"] == "Europa" for r in rows)


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
    result = run_scrape(offline=True)
    rows = result.ranked_offers(max_price_eur=150)
    assert rows, "powinny być jakieś tanie oferty"
    assert all(r["price_eur"] <= 150 for r in rows)


def test_best_per_race_unique_races():
    result = run_scrape(offline=True)
    rows = result.best_per_race()
    keys = [r["race_key"] for r in rows]
    assert len(keys) == len(set(keys)), "duplikaty wyścigów w best_per_race"


def test_sort_by_price_ascending():
    result = run_scrape(offline=True)
    rows = result.ranked_offers(sort_by="price")
    prices = [r["price_eur"] for r in rows]
    assert prices == sorted(prices)
