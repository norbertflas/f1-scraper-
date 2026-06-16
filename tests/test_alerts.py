"""Testy systemu alertów (dopasowanie, deduplikacja, kanały) – offline."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from f1scraper.alerts import (  # noqa: E402
    AlertCriteria,
    Notifier,
    find_matches,
    offer_signature,
    run_alerts,
)
from f1scraper.engine import run_scrape  # noqa: E402


class RecordingNotifier(Notifier):
    def __init__(self):
        self.calls = []

    def send(self, subject, matches):
        self.calls.append((subject, matches))


def test_find_matches_respects_criteria():
    result = run_scrape()
    crit = AlertCriteria(
        name="Monza tanio", races=["Italian Grand Prix"], max_price_eur=300
    )
    rows = find_matches(result, crit)
    assert rows
    assert all(r["race_name"] == "Italian Grand Prix" for r in rows)
    assert all(r["price_eur"] <= 300 for r in rows)


def test_run_alerts_dedupes(tmp_path):
    result = run_scrape()
    state = tmp_path / "state.json"
    crit = [AlertCriteria(name="tanie tory", source_type="circuit", max_price_eur=200)]
    notifier = RecordingNotifier()

    first = run_alerts(crit, notifier, result=result, state_path=state)
    assert first, "pierwszy przebieg powinien znaleźć trafienia"

    notifier2 = RecordingNotifier()
    second = run_alerts(crit, notifier2, result=result, state_path=state)
    assert second == [], "drugi przebieg nie powinien powtórzyć tych samych ofert"
    assert notifier2.calls == []


def test_offer_signature_changes_with_price():
    base = {"race_key": "italian-grand-prix", "grandstand": "X",
            "source_name": "Monza", "price_eur": 100, "availability": "dostępne"}
    changed = {**base, "price_eur": 120}
    assert offer_signature(base) != offer_signature(changed)


def test_criteria_from_dict_roundtrip():
    crit = AlertCriteria.from_dict({
        "name": "test", "races": ["Monaco Grand Prix"],
        "max_price_eur": 500, "min_seat_quality": 7, "covered_only": True,
    })
    assert crit.matches_race("Monaco Grand Prix")
    assert not crit.matches_race("Italian Grand Prix")
    assert crit.to_filters()["covered_only"] is True
