"""Silnik: uruchamia scrapery, scala dane i liczy ranking ofert."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .fetch import PoliteFetcher
from .models import Race, TicketOffer
from .registry import build_scrapers

log = logging.getLogger("f1scraper.engine")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_PATH = DATA_DIR / "results.json"


class ScrapeResult:
    """Wynik jednego przebiegu: wyścigi + oferty + metadane."""

    def __init__(
        self,
        races: list[Race],
        offers: list[TicketOffer],
        scraped_at: Optional[str] = None,
    ) -> None:
        self.races = races
        self.offers = offers
        self.scraped_at = scraped_at or datetime.utcnow().isoformat()
        self._race_by_key = {r.key: r for r in races}

    # -- ranking / filtrowanie -----------------------------------------
    def race_popularity(self, race_key: str) -> float:
        race = self._race_by_key.get(race_key)
        return race.popularity if race else 3.0

    def ranked_offers(
        self,
        *,
        max_price_eur: Optional[float] = None,
        min_seat_quality: Optional[float] = None,
        country: Optional[str] = None,
        source_type: Optional[str] = None,
        covered_only: bool = False,
        available_only: bool = True,
        upcoming_only: bool = False,
        sort_by: str = "value",
    ) -> list[dict]:
        """Zwraca oferty (jako dict) przefiltrowane i posortowane."""
        today = date.today()
        rows: list[dict] = []
        for offer in self.offers:
            race = self._race_by_key.get(offer.race_key)
            pop = race.popularity if race else 3.0

            if available_only and not offer.is_available:
                continue
            if max_price_eur is not None and offer.price_eur > max_price_eur:
                continue
            if min_seat_quality is not None and offer.seat_quality < min_seat_quality:
                continue
            if covered_only and not offer.covered:
                continue
            if source_type and offer.source_type != source_type:
                continue
            if country and race and race.country.lower() != country.lower():
                continue
            if upcoming_only and race and race.date_end and race.date_end < today:
                continue

            row = offer.to_dict(pop)
            row["race_name"] = race.name if race else offer.race_key
            row["race_date"] = race.date_label if race else ""
            row["country"] = race.country if race else ""
            row["city"] = race.city if race else ""
            rows.append(row)

        rows.sort(key=_sort_key(sort_by), reverse=_sort_desc(sort_by))
        return rows

    def best_per_race(self, **filters) -> list[dict]:
        """Najlepsza (wg value_score) oferta dla każdego wyścigu."""
        filters.setdefault("sort_by", "value")
        best: dict[str, dict] = {}
        for row in self.ranked_offers(**filters):
            key = row["race_key"]
            if key not in best:  # już posortowane wg wartości malejąco
                best[key] = row
        return list(best.values())

    def countries(self) -> list[str]:
        return sorted({r.country for r in self.races if r.country})

    # -- serializacja ---------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "scraped_at": self.scraped_at,
            "races": [r.to_dict() for r in self.races],
            "offers": [
                o.to_dict(self.race_popularity(o.race_key)) for o in self.offers
            ],
            "stats": {
                "races": len(self.races),
                "offers": len(self.offers),
                "available": sum(1 for o in self.offers if o.is_available),
            },
        }

    def save(self, path: Path = RESULTS_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        log.info("Zapisano wyniki do %s", path)


def _sort_key(sort_by: str):
    if sort_by == "price":
        return lambda r: r["price_eur"]
    if sort_by == "quality":
        return lambda r: r["seat_quality"]
    if sort_by == "date":
        return lambda r: r.get("race_date", "")
    return lambda r: r["value_score"]  # domyślnie


def _sort_desc(sort_by: str) -> bool:
    # Cena rosnąco (taniej = lepiej na górze), reszta malejąco.
    return sort_by != "price"


def run_scrape(
    respect_robots: bool = True,
    use_cache: bool = True,
) -> ScrapeResult:
    """Uruchamia wszystkie scrapery i zwraca scalony wynik."""
    fetcher = PoliteFetcher(respect_robots=respect_robots)
    if not use_cache:
        fetcher.cache_ttl = 0

    scrapers = build_scrapers(fetcher)
    all_races: dict[str, Race] = {}
    all_offers: list[TicketOffer] = []

    for scraper in scrapers:
        races, offers = scraper.safe_scrape()
        for race in races:
            # Pierwszy scraper (kalendarz) ustala kanon; kolejne nie nadpisują.
            all_races.setdefault(race.key, race)
        all_offers.extend(offers)

    result = ScrapeResult(list(all_races.values()), all_offers)
    return result


def load_results(path: Path = RESULTS_PATH) -> Optional[ScrapeResult]:
    """Wczytuje ostatni zapisany wynik (bez ponownego scrapowania)."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    races = [_race_from_dict(r) for r in data.get("races", [])]
    offers = [_offer_from_dict(o) for o in data.get("offers", [])]
    return ScrapeResult(races, offers, scraped_at=data.get("scraped_at"))


def _race_from_dict(d: dict) -> Race:
    return Race(
        round=d.get("round", 0),
        name=d.get("name", ""),
        circuit=d.get("circuit", ""),
        country=d.get("country", ""),
        city=d.get("city", ""),
        date_start=_parse_date(d.get("date_start")),
        date_end=_parse_date(d.get("date_end")),
        official_url=d.get("official_url", ""),
        popularity=d.get("popularity", 3.0),
    )


def _offer_from_dict(d: dict) -> TicketOffer:
    return TicketOffer(
        race_key=d.get("race_key", ""),
        source_type=d.get("source_type", "calendar"),
        source_name=d.get("source_name", ""),
        grandstand=d.get("grandstand", ""),
        category=d.get("category", ""),
        price=d.get("price", 0.0),
        currency=d.get("currency", "EUR"),
        seat_quality=d.get("seat_quality", 5.0),
        covered=d.get("covered", False),
        view_notes=d.get("view_notes", ""),
        availability=d.get("availability", "dostępne"),
        buy_url=d.get("buy_url", ""),
        scraped_at=d.get("scraped_at", datetime.utcnow().isoformat()),
    )


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
