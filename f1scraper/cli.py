"""Interfejs wiersza poleceń.

Przykłady:
    python -m f1scraper.cli refresh                 # zescrapuj i zapisz wyniki
    python -m f1scraper.cli top --max-price 400     # pokaż najlepsze okazje
    python -m f1scraper.cli top --sort price --limit 10
"""

from __future__ import annotations

import argparse
import logging
import sys

from .engine import load_results, run_scrape


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="f1scraper", description="F1 ticket scraper")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="więcej logów"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ref = sub.add_parser("refresh", help="zescrapuj źródła i zapisz wyniki")
    p_ref.add_argument(
        "--no-robots", action="store_true", help="ignoruj robots.txt (na własną odpowiedzialność)"
    )
    p_ref.add_argument("--no-cache", action="store_true", help="pomiń cache HTTP")

    p_top = sub.add_parser("top", help="pokaż najlepsze oferty")
    p_top.add_argument("--max-price", type=float, default=None, help="maks. cena (EUR)")
    p_top.add_argument("--min-quality", type=float, default=None, help="min. jakość miejsca 1-10")
    p_top.add_argument("--country", default=None, help="filtr kraju")
    p_top.add_argument("--source", default=None, choices=["circuit", "partner", "calendar"])
    p_top.add_argument("--covered", action="store_true", help="tylko zadaszone")
    p_top.add_argument("--sort", default="value", choices=["value", "price", "quality", "date"])
    p_top.add_argument("--limit", type=int, default=15)
    p_top.add_argument("--best-per-race", action="store_true", help="jedna najlepsza oferta na wyścig")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.cmd == "refresh":
        result = run_scrape(
            respect_robots=not args.no_robots, use_cache=not args.no_cache
        )
        result.save()
        print(
            f"Gotowe: {len(result.races)} wyścigów, {len(result.offers)} ofert "
            f"(zapisano do data/results.json)."
        )
        return 0

    if args.cmd == "top":
        result = load_results()
        if result is None:
            print("Brak zapisanych wyników – uruchom najpierw: f1scraper refresh")
            return 1
        filters = dict(
            max_price_eur=args.max_price,
            min_seat_quality=args.min_quality,
            country=args.country,
            source_type=args.source,
            covered_only=args.covered,
            sort_by=args.sort,
        )
        rows = (
            result.best_per_race(**filters)
            if args.best_per_race
            else result.ranked_offers(**filters)
        )
        _print_table(rows[: args.limit])
        return 0

    return 1


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("Brak ofert spełniających kryteria.")
        return
    print(
        f"{'WYŚCIG':<26}{'TRYBUNA':<26}{'CENA':>9}  {'JAKOŚĆ':>6}  {'WARTOŚĆ':>7}  ŹRÓDŁO"
    )
    print("-" * 100)
    for r in rows:
        print(
            f"{_t(r['race_name'],25):<26}"
            f"{_t(r['grandstand'],25):<26}"
            f"{r['price_eur']:>7.0f}€  "
            f"{r['seat_quality']:>6.1f}  "
            f"{r['value_score']:>7.1f}  "
            f"{r['source_name']}"
        )


def _t(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


if __name__ == "__main__":
    sys.exit(main())
