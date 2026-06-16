"""Modele danych dla wyścigów i ofert biletowych."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

# Statyczne, przybliżone kursy do normalizacji ceny względem EUR.
# To celowo uproszczenie – do rankingu "wartości" wystarczy rząd wielkości.
FX_TO_EUR: dict[str, float] = {
    "EUR": 1.0,
    "PLN": 0.23,
    "GBP": 1.17,
    "USD": 0.92,
    "CHF": 1.05,
    "AED": 0.25,
    "AUD": 0.60,
    "SGD": 0.68,
    "BRL": 0.16,
    "MXN": 0.05,
    "QAR": 0.25,
    "SAR": 0.25,
    "JPY": 0.0061,
    "CAD": 0.68,
}


@dataclass
class Race:
    """Pojedynczy wyścig (weekend Grand Prix)."""

    round: int
    name: str  # np. "Italian Grand Prix"
    circuit: str  # np. "Autodromo Nazionale Monza"
    country: str
    city: str
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    official_url: str = ""
    # Subiektywna popularność/atrakcyjność wyścigu (1–5). Używana w rankingu
    # "dobrego wyścigu". Można później wyliczać z danych (frekwencja, opinie).
    popularity: float = 3.0

    @property
    def key(self) -> str:
        """Stabilny klucz do łączenia wyścigów z różnych źródeł."""
        return _slug(self.name)

    @property
    def date_label(self) -> str:
        if self.date_start and self.date_end:
            return f"{self.date_start:%d.%m} – {self.date_end:%d.%m.%Y}"
        if self.date_start:
            return f"{self.date_start:%d.%m.%Y}"
        return "termin TBA"

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["date_start"] = self.date_start.isoformat() if self.date_start else None
        d["date_end"] = self.date_end.isoformat() if self.date_end else None
        d["key"] = self.key
        d["date_label"] = self.date_label
        return d


@dataclass
class TicketOffer:
    """Pojedyncza oferta biletowa powiązana z wyścigiem."""

    race_key: str  # Race.key, do którego należy oferta
    source_type: str  # "calendar" | "circuit" | "partner"
    source_name: str  # np. "Monza (oficjalna)", "GooTickets"
    grandstand: str  # np. "Tribuna Centrale", "General Admission"
    category: str  # np. "Weekend 3-dniowy", "Niedziela"
    price: float
    currency: str = "EUR"
    # Jakość miejsca w skali 1–10 (10 = idealny widok, np. start/meta, zadaszenie).
    seat_quality: float = 5.0
    covered: bool = False
    view_notes: str = ""
    availability: str = "dostępne"  # "dostępne" | "ostatnie" | "wyprzedane"
    buy_url: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def price_eur(self) -> float:
        rate = FX_TO_EUR.get(self.currency.upper(), 1.0)
        return round(self.price * rate, 2)

    @property
    def is_available(self) -> bool:
        return self.availability != "wyprzedane"

    def value_score(self, race_popularity: float = 3.0) -> float:
        """Wynik 'wartości' oferty: im wyższy, tym lepszy deal.

        Łączy jakość miejsca, atrakcyjność wyścigu i przystępność ceny.
        Dostępność modyfikuje wynik (wyprzedane = 0).
        """
        if not self.is_available:
            return 0.0
        price = max(self.price_eur, 1.0)
        # Popularność (1–5) przeskalowana do mnożnika ~0.6–1.4.
        pop_factor = 0.6 + (race_popularity / 5.0) * 0.8
        raw = (self.seat_quality * pop_factor) / price
        # Skalujemy do czytelnego zakresu (~0–100).
        score = raw * 1000
        if self.availability == "ostatnie":
            score *= 0.95  # lekko karzemy ryzyko, że bilet zniknie
        return round(score, 1)

    def to_dict(self, race_popularity: float = 3.0) -> dict:
        d = dataclasses.asdict(self)
        d["price_eur"] = self.price_eur
        d["value_score"] = self.value_score(race_popularity)
        d["is_available"] = self.is_available
        return d


def _slug(text: str) -> str:
    out = []
    for ch in text.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in " -_":
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")
