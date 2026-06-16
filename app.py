"""Web dashboard scrapera biletów F1 (Flask).

Uruchomienie:
    pip install -r requirements.txt
    python app.py            # http://127.0.0.1:5000

Dashboard pokazuje posortowane oferty (cena, jakość miejsca, wartość) z
filtrami. Dane wczytywane są z data/results.json; przycisk "Odśwież" lub
endpoint /refresh uruchamia scrapowanie na nowo.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, redirect, render_template, request, url_for

from f1scraper.engine import load_results, run_scrape

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = Flask(__name__)


def _get_result():
    """Zwraca ostatni wynik; gdy brak – scrapuje i zapisuje."""
    result = load_results()
    if result is None:
        result = run_scrape()
        result.save()
    return result


def _filters_from_request() -> dict:
    def f(name, cast, default=None):
        raw = request.args.get(name)
        if raw is None or raw == "":
            return default
        try:
            return cast(raw)
        except (ValueError, TypeError):
            return default

    return dict(
        max_price_eur=f("max_price", float),
        min_seat_quality=f("min_quality", float),
        country=f("country", str),
        source_type=f("source", str),
        covered_only=request.args.get("covered") == "1",
        upcoming_only=request.args.get("upcoming") == "1",
        sort_by=request.args.get("sort", "value"),
    )


@app.route("/")
def index():
    result = _get_result()
    filters = _filters_from_request()
    best_per_race = request.args.get("best") == "1"

    rows = (
        result.best_per_race(**filters)
        if best_per_race
        else result.ranked_offers(**filters)
    )

    return render_template(
        "index.html",
        rows=rows,
        countries=result.countries(),
        scraped_at=result.scraped_at,
        args=request.args,
        best_per_race=best_per_race,
        total_offers=len(result.offers),
        total_races=len(result.races),
    )


@app.route("/api/offers")
def api_offers():
    result = _get_result()
    rows = result.ranked_offers(**_filters_from_request())
    return jsonify({"scraped_at": result.scraped_at, "count": len(rows), "offers": rows})


@app.route("/refresh", methods=["POST", "GET"])
def refresh():
    result = run_scrape()
    result.save()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
