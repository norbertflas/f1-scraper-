"""Współdzielone narzędzia do parsowania stron biletowych.

Zawiera:
  * ``parse_price`` – odporne wyciąganie liczby z ceny ("1.234,50 €", "£295", ...),
  * ``detect_currency`` – wykrywanie waluty po symbolu/kodzie,
  * ``extract_jsonld_offers`` – parsowanie danych strukturalnych schema.org
    (Event/Product + offers), które wiele serwisów biletowych publikuje,
  * ``guess_seat_quality`` / ``guess_covered`` – heurystyki oceny miejsca
    na podstawie nazwy trybuny.

Te funkcje są czyste i testowalne offline (na fixture'ach HTML), niezależnie
od dostępu do sieci.
"""

from __future__ import annotations

import json
import re
from typing import Optional

from bs4 import BeautifulSoup

# Symbol/kod waluty -> kod ISO.
_CURRENCY_SYMBOLS = {
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
    "$": "USD", "usd": "USD",
    "zł": "PLN", "pln": "PLN",
    "chf": "CHF", "fr": "CHF",
    "aed": "AED", "aud": "AUD", "sgd": "SGD",
    "brl": "BRL", "r$": "BRL", "mxn": "MXN",
    "qar": "QAR", "sar": "SAR", "¥": "JPY", "jpy": "JPY", "cad": "CAD",
}


def parse_price(text: str) -> Optional[float]:
    """Wyciąga kwotę z dowolnego zapisu ceny.

    Obsługuje separatory tysięcy i dwa style dziesiętne:
      "1.234,50 €" -> 1234.50   (europejski: kropka=tysiące, przecinek=ułamek)
      "1,234.50"   -> 1234.50   (anglosaski: przecinek=tysiące, kropka=ułamek)
      "£295"       -> 295.0
    """
    if not text:
        return None
    m = re.search(r"\d[\d.,\s ]*\d|\d", text)
    if not m:
        return None
    num = re.sub(r"[\s ]", "", m.group(0))

    has_comma = "," in num
    has_dot = "." in num
    if has_comma and has_dot:
        # Ostatni separator decyduje o tym, co jest częścią ułamkową.
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")  # europejski
        else:
            num = num.replace(",", "")  # anglosaski
    elif has_comma:
        # Przecinek jako dziesiętny tylko gdy wygląda jak ułamek (",dd").
        if re.search(r",\d{1,2}$", num):
            num = num.replace(",", ".")
        else:
            num = num.replace(",", "")
    try:
        return round(float(num), 2)
    except ValueError:
        return None


def detect_currency(text: str, default: str = "EUR") -> str:
    low = text.lower()
    for token, code in _CURRENCY_SYMBOLS.items():
        if token in low:
            return code
    return default


def guess_covered(name: str) -> bool:
    low = name.lower()
    return any(k in low for k in ("covered", "zadasz", "roof", "coperta", "couvert"))


def guess_seat_quality(name: str) -> float:
    """Szacuje jakość miejsca (1–10) z nazwy trybuny/kategorii."""
    low = name.lower()
    q = 5.0
    if any(k in low for k in ("general admission", "ga", "prato", "lawn", "standing")):
        q = 3.0
    if any(k in low for k in ("grandstand", "tribun", "stand")):
        q = max(q, 6.0)
    if any(k in low for k in ("start", "finish", "main", "principal", "centrale", "pit", "podium")):
        q = max(q, 8.5)
    if any(k in low for k in ("premium", "vip", "paddock", "club", "hospitality", "gold")):
        q = max(q, 9.5)
    if guess_covered(name):
        q = min(10.0, q + 0.5)
    return round(q, 1)


# Mapowanie schema.org availability -> nasz status.
_AVAILABILITY = {
    "instock": "dostępne",
    "limitedavailability": "ostatnie",
    "soldout": "wyprzedane",
    "outofstock": "wyprzedane",
    "preorder": "dostępne",
}


def _norm_availability(value: str) -> str:
    if not value:
        return "dostępne"
    token = value.rsplit("/", 1)[-1].lower()
    return _AVAILABILITY.get(token, "dostępne")


def _iter_jsonld(html: str):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                yield from data["@graph"]
            else:
                yield data


def extract_jsonld_offers(html: str) -> list[dict]:
    """Wyciąga oferty z danych strukturalnych schema.org.

    Zwraca listę słowników: name, price, currency, availability, url.
    Działa dla węzłów typu Event/Product z polem ``offers`` (pojedyncza
    oferta lub lista).
    """
    results: list[dict] = []
    for node in _iter_jsonld(html):
        if not isinstance(node, dict):
            continue
        base_name = _text(node.get("name"))
        offers = node.get("offers")
        if offers is None:
            continue
        if isinstance(offers, dict):
            offers = [offers]
        if not isinstance(offers, list):
            continue
        for off in offers:
            if not isinstance(off, dict):
                continue
            price = off.get("price") or off.get("lowPrice")
            price_val = parse_price(str(price)) if price is not None else None
            if price_val is None:
                continue
            name = _text(off.get("name")) or base_name or "Bilet"
            results.append(
                {
                    "name": name,
                    "price": price_val,
                    "currency": (off.get("priceCurrency") or "EUR").upper(),
                    "availability": _norm_availability(_text(off.get("availability"))),
                    "url": _text(off.get("url")),
                }
            )
    return results


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return _text(value[0]) if value else ""
    return str(value).strip()
