"""Wbudowane dane zapasowe (fallback).

Używane, gdy scrapowanie na żywo się nie powiedzie (403/anty-bot, brak sieci,
zmiana układu strony). Dzięki temu dashboard zawsze ma co pokazać, a strukturę
danych łatwo porównać z tym, co zwracają scrapery na żywo.

Kalendarz 2026 jest przybliżony – służy jako demo, nie jako źródło prawdy.
"""

from __future__ import annotations

from datetime import date

from .models import Race, TicketOffer

# (round, name, circuit, country, city, start, end, popularity)
_CALENDAR_2026 = [
    (1, "Australian Grand Prix", "Albert Park Circuit", "Australia", "Melbourne", (2026, 3, 6), (2026, 3, 8), 4.0),
    (2, "Chinese Grand Prix", "Shanghai International Circuit", "China", "Shanghai", (2026, 3, 13), (2026, 3, 15), 3.5),
    (3, "Japanese Grand Prix", "Suzuka Circuit", "Japan", "Suzuka", (2026, 3, 27), (2026, 3, 29), 4.5),
    (4, "Bahrain Grand Prix", "Bahrain International Circuit", "Bahrain", "Sakhir", (2026, 4, 10), (2026, 4, 12), 3.5),
    (5, "Saudi Arabian Grand Prix", "Jeddah Corniche Circuit", "Saudi Arabia", "Jeddah", (2026, 4, 17), (2026, 4, 19), 3.5),
    (6, "Miami Grand Prix", "Miami International Autodrome", "USA", "Miami", (2026, 5, 1), (2026, 5, 3), 4.0),
    (7, "Canadian Grand Prix", "Circuit Gilles Villeneuve", "Canada", "Montreal", (2026, 5, 22), (2026, 5, 24), 4.0),
    (8, "Monaco Grand Prix", "Circuit de Monaco", "Monaco", "Monte Carlo", (2026, 6, 5), (2026, 6, 7), 5.0),
    (9, "Spanish Grand Prix", "Circuit de Barcelona-Catalunya", "Spain", "Barcelona", (2026, 6, 12), (2026, 6, 14), 3.5),
    (10, "Austrian Grand Prix", "Red Bull Ring", "Austria", "Spielberg", (2026, 6, 26), (2026, 6, 28), 4.5),
    (11, "British Grand Prix", "Silverstone Circuit", "United Kingdom", "Silverstone", (2026, 7, 3), (2026, 7, 5), 5.0),
    (12, "Belgian Grand Prix", "Circuit de Spa-Francorchamps", "Belgium", "Spa", (2026, 7, 17), (2026, 7, 19), 5.0),
    (13, "Hungarian Grand Prix", "Hungaroring", "Hungary", "Budapest", (2026, 7, 24), (2026, 7, 26), 3.5),
    (14, "Dutch Grand Prix", "Circuit Zandvoort", "Netherlands", "Zandvoort", (2026, 8, 21), (2026, 8, 23), 4.5),
    (15, "Italian Grand Prix", "Autodromo Nazionale Monza", "Italy", "Monza", (2026, 9, 4), (2026, 9, 6), 5.0),
    (16, "Madrid Grand Prix", "Madring Circuit", "Spain", "Madrid", (2026, 9, 11), (2026, 9, 13), 4.0),
    (17, "Azerbaijan Grand Prix", "Baku City Circuit", "Azerbaijan", "Baku", (2026, 9, 25), (2026, 9, 27), 3.5),
    (18, "Singapore Grand Prix", "Marina Bay Street Circuit", "Singapore", "Singapore", (2026, 10, 9), (2026, 10, 11), 4.5),
    (19, "United States Grand Prix", "Circuit of the Americas", "USA", "Austin", (2026, 10, 23), (2026, 10, 25), 4.5),
    (20, "Mexico City Grand Prix", "Autodromo Hermanos Rodriguez", "Mexico", "Mexico City", (2026, 10, 30), (2026, 11, 1), 4.5),
    (21, "Sao Paulo Grand Prix", "Autodromo Jose Carlos Pace", "Brazil", "Sao Paulo", (2026, 11, 6), (2026, 11, 8), 4.5),
    (22, "Las Vegas Grand Prix", "Las Vegas Strip Circuit", "USA", "Las Vegas", (2026, 11, 19), (2026, 11, 21), 4.0),
    (23, "Qatar Grand Prix", "Lusail International Circuit", "Qatar", "Lusail", (2026, 11, 26), (2026, 11, 28), 3.5),
    (24, "Abu Dhabi Grand Prix", "Yas Marina Circuit", "UAE", "Abu Dhabi", (2026, 12, 4), (2026, 12, 6), 4.0),
]


def calendar_2026() -> list[Race]:
    races = []
    for rnd, name, circuit, country, city, start, end, pop in _CALENDAR_2026:
        races.append(
            Race(
                round=rnd,
                name=name,
                circuit=circuit,
                country=country,
                city=city,
                date_start=date(*start),
                date_end=date(*end),
                official_url="https://www.formula1.com/en/racing/2026.html",
                popularity=pop,
            )
        )
    return races


def race_by_name(name: str) -> Race | None:
    for race in calendar_2026():
        if race.name == name:
            return race
    return None


def sample_offers_for(
    race_name: str,
    source_type: str,
    source_name: str,
    base_currency: str,
    base_url: str,
    price_multiplier: float = 1.0,
) -> list[TicketOffer]:
    """Generuje zestaw typowych ofert (trybuny + GA) dla danego wyścigu.

    Ceny są przybliżone i przeskalowane ``price_multiplier`` – partnerzy
    bywają droższi niż sprzedaż oficjalna toru.
    """
    race = race_by_name(race_name)
    if race is None:
        return []

    m = price_multiplier
    blueprint = [
        # (trybuna, kategoria, cena, jakość 1-10, zadaszenie, notatka, dostępność)
        ("General Admission", "Weekend 3-dniowy", 110, 3.0, False, "Wstęp na tereny ogólne, bez numerowanego miejsca", "dostępne"),
        ("Tribune – łuk", "Weekend 3-dniowy", 280, 6.0, False, "Dobry widok na zakręt, sporo akcji", "dostępne"),
        ("Tribune – start/meta", "Weekend 3-dniowy", 470, 8.5, True, "Widok na start, pit-lane i podium, częściowe zadaszenie", "ostatnie"),
        ("Trybuna główna – Premium", "Weekend 3-dniowy", 690, 9.5, True, "Najlepszy widok, zadaszenie, blisko padoku", "dostępne"),
        ("Tribune – niedziela", "Niedziela (wyścig)", 190, 6.5, False, "Tylko dzień wyścigu", "dostępne"),
    ]

    offers: list[TicketOffer] = []
    for grandstand, category, price, quality, covered, note, avail in blueprint:
        offers.append(
            TicketOffer(
                race_key=race.key,
                source_type=source_type,
                source_name=source_name,
                grandstand=grandstand,
                category=category,
                price=round(price * m, 2),
                currency=base_currency,
                seat_quality=quality,
                covered=covered,
                view_notes=note,
                availability=avail,
                buy_url=base_url,
            )
        )
    return offers
