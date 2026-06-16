"""Wbudowane dane zapasowe (fallback).

Używane, gdy scrapowanie na żywo się nie powiedzie (403/anty-bot, brak sieci,
zmiana układu strony). Dzięki temu dashboard zawsze ma co pokazać, a strukturę
danych łatwo porównać z tym, co zwracają scrapery na żywo.

Kalendarze są przybliżone i służą jako demo, nie jako źródło prawdy. Kalendarz
2027 nie jest jeszcze oficjalnie potwierdzony przez F1 – daty/ceny to realistyczny
szablon do aktualizacji po publikacji oficjalnego terminarza.
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional

from .models import Race, TicketOffer

# (round, name, circuit, country, city, start, end, popularity, weekend_days)
_CALENDAR_2026 = [
    (1, "Australian Grand Prix", "Albert Park Circuit", "Australia", "Melbourne", (2026, 3, 6), (2026, 3, 8), 4.0, 3),
    (2, "Chinese Grand Prix", "Shanghai International Circuit", "China", "Shanghai", (2026, 3, 13), (2026, 3, 15), 3.5, 3),
    (3, "Japanese Grand Prix", "Suzuka Circuit", "Japan", "Suzuka", (2026, 3, 27), (2026, 3, 29), 4.5, 3),
    (4, "Bahrain Grand Prix", "Bahrain International Circuit", "Bahrain", "Sakhir", (2026, 4, 10), (2026, 4, 12), 3.5, 3),
    (5, "Saudi Arabian Grand Prix", "Jeddah Corniche Circuit", "Saudi Arabia", "Jeddah", (2026, 4, 17), (2026, 4, 19), 3.5, 3),
    (6, "Miami Grand Prix", "Miami International Autodrome", "USA", "Miami", (2026, 5, 1), (2026, 5, 3), 4.0, 3),
    (7, "Canadian Grand Prix", "Circuit Gilles Villeneuve", "Canada", "Montreal", (2026, 5, 22), (2026, 5, 24), 4.0, 3),
    (8, "Monaco Grand Prix", "Circuit de Monaco", "Monaco", "Monte Carlo", (2026, 6, 4), (2026, 6, 7), 5.0, 4),
    (9, "Spanish Grand Prix", "Circuit de Barcelona-Catalunya", "Spain", "Barcelona", (2026, 6, 12), (2026, 6, 14), 3.5, 3),
    (10, "Austrian Grand Prix", "Red Bull Ring", "Austria", "Spielberg", (2026, 6, 26), (2026, 6, 28), 4.5, 3),
    (11, "British Grand Prix", "Silverstone Circuit", "United Kingdom", "Silverstone", (2026, 7, 3), (2026, 7, 5), 5.0, 3),
    (12, "Belgian Grand Prix", "Circuit de Spa-Francorchamps", "Belgium", "Spa", (2026, 7, 17), (2026, 7, 19), 5.0, 3),
    (13, "Hungarian Grand Prix", "Hungaroring", "Hungary", "Budapest", (2026, 7, 24), (2026, 7, 26), 3.5, 3),
    (14, "Dutch Grand Prix", "Circuit Zandvoort", "Netherlands", "Zandvoort", (2026, 8, 21), (2026, 8, 23), 4.5, 3),
    (15, "Italian Grand Prix", "Autodromo Nazionale Monza", "Italy", "Monza", (2026, 9, 4), (2026, 9, 6), 5.0, 3),
    (16, "Madrid Grand Prix", "Madring Circuit", "Spain", "Madrid", (2026, 9, 11), (2026, 9, 13), 4.0, 3),
    (17, "Azerbaijan Grand Prix", "Baku City Circuit", "Azerbaijan", "Baku", (2026, 9, 25), (2026, 9, 27), 3.5, 3),
    (18, "Singapore Grand Prix", "Marina Bay Street Circuit", "Singapore", "Singapore", (2026, 10, 9), (2026, 10, 11), 4.5, 3),
    (19, "United States Grand Prix", "Circuit of the Americas", "USA", "Austin", (2026, 10, 23), (2026, 10, 25), 4.5, 3),
    (20, "Mexico City Grand Prix", "Autodromo Hermanos Rodriguez", "Mexico", "Mexico City", (2026, 10, 30), (2026, 11, 1), 4.5, 3),
    (21, "Sao Paulo Grand Prix", "Autodromo Jose Carlos Pace", "Brazil", "Sao Paulo", (2026, 11, 6), (2026, 11, 8), 4.5, 3),
    (22, "Las Vegas Grand Prix", "Las Vegas Strip Circuit", "USA", "Las Vegas", (2026, 11, 19), (2026, 11, 21), 4.0, 3),
    (23, "Qatar Grand Prix", "Lusail International Circuit", "Qatar", "Lusail", (2026, 11, 26), (2026, 11, 28), 3.5, 3),
    (24, "Abu Dhabi Grand Prix", "Yas Marina Circuit", "UAE", "Abu Dhabi", (2026, 12, 4), (2026, 12, 6), 4.0, 3),
]

# Kalendarz 2027 – realistyczny szablon (do potwierdzenia przez F1).
# Monaco jako weekend 4-dniowy (czwartek–niedziela), Abu Dhabi jako finał sezonu.
_CALENDAR_2027 = [
    (1, "Australian Grand Prix", "Albert Park Circuit", "Australia", "Melbourne", (2027, 3, 5), (2027, 3, 7), 4.0, 3),
    (2, "Chinese Grand Prix", "Shanghai International Circuit", "China", "Shanghai", (2027, 3, 19), (2027, 3, 21), 3.5, 3),
    (3, "Japanese Grand Prix", "Suzuka Circuit", "Japan", "Suzuka", (2027, 4, 9), (2027, 4, 11), 4.5, 3),
    (4, "Bahrain Grand Prix", "Bahrain International Circuit", "Bahrain", "Sakhir", (2027, 4, 16), (2027, 4, 18), 3.5, 3),
    (5, "Saudi Arabian Grand Prix", "Jeddah Corniche Circuit", "Saudi Arabia", "Jeddah", (2027, 4, 23), (2027, 4, 25), 3.5, 3),
    (6, "Miami Grand Prix", "Miami International Autodrome", "USA", "Miami", (2027, 5, 7), (2027, 5, 9), 4.0, 3),
    (7, "Canadian Grand Prix", "Circuit Gilles Villeneuve", "Canada", "Montreal", (2027, 5, 21), (2027, 5, 23), 4.0, 3),
    (8, "Monaco Grand Prix", "Circuit de Monaco", "Monaco", "Monte Carlo", (2027, 6, 3), (2027, 6, 6), 5.0, 4),
    (9, "Spanish Grand Prix", "Circuit de Barcelona-Catalunya", "Spain", "Barcelona", (2027, 6, 11), (2027, 6, 13), 3.5, 3),
    (10, "Austrian Grand Prix", "Red Bull Ring", "Austria", "Spielberg", (2027, 6, 25), (2027, 6, 27), 4.5, 3),
    (11, "British Grand Prix", "Silverstone Circuit", "United Kingdom", "Silverstone", (2027, 7, 2), (2027, 7, 4), 5.0, 3),
    (12, "Belgian Grand Prix", "Circuit de Spa-Francorchamps", "Belgium", "Spa", (2027, 7, 23), (2027, 7, 25), 5.0, 3),
    (13, "Hungarian Grand Prix", "Hungaroring", "Hungary", "Budapest", (2027, 7, 30), (2027, 8, 1), 3.5, 3),
    (14, "Dutch Grand Prix", "Circuit Zandvoort", "Netherlands", "Zandvoort", (2027, 8, 27), (2027, 8, 29), 4.5, 3),
    (15, "Italian Grand Prix", "Autodromo Nazionale Monza", "Italy", "Monza", (2027, 9, 3), (2027, 9, 5), 5.0, 3),
    (16, "Madrid Grand Prix", "Madring Circuit", "Spain", "Madrid", (2027, 9, 10), (2027, 9, 12), 4.0, 3),
    (17, "Azerbaijan Grand Prix", "Baku City Circuit", "Azerbaijan", "Baku", (2027, 9, 24), (2027, 9, 26), 3.5, 3),
    (18, "Singapore Grand Prix", "Marina Bay Street Circuit", "Singapore", "Singapore", (2027, 10, 8), (2027, 10, 10), 4.5, 3),
    (19, "United States Grand Prix", "Circuit of the Americas", "USA", "Austin", (2027, 10, 22), (2027, 10, 24), 4.5, 3),
    (20, "Mexico City Grand Prix", "Autodromo Hermanos Rodriguez", "Mexico", "Mexico City", (2027, 10, 29), (2027, 10, 31), 4.5, 3),
    (21, "Sao Paulo Grand Prix", "Autodromo Jose Carlos Pace", "Brazil", "Sao Paulo", (2027, 11, 5), (2027, 11, 7), 4.5, 3),
    (22, "Las Vegas Grand Prix", "Las Vegas Strip Circuit", "USA", "Las Vegas", (2027, 11, 18), (2027, 11, 20), 4.0, 3),
    (23, "Qatar Grand Prix", "Lusail International Circuit", "Qatar", "Lusail", (2027, 11, 25), (2027, 11, 27), 3.5, 3),
    (24, "Abu Dhabi Grand Prix", "Yas Marina Circuit", "UAE", "Abu Dhabi", (2027, 12, 3), (2027, 12, 5), 4.5, 3),
]

_SEASONS: dict[int, list] = {2026: _CALENDAR_2026, 2027: _CALENDAR_2027}

#: Sezony obsługiwane przez narzędzie.
SEASONS: list[int] = sorted(_SEASONS)


def calendar(year: int) -> list[Race]:
    races = []
    for rnd, name, circuit, country, city, start, end, pop, days in _SEASONS.get(year, []):
        races.append(
            Race(
                round=rnd,
                name=name,
                circuit=circuit,
                country=country,
                city=city,
                date_start=date(*start),
                date_end=date(*end),
                official_url=f"https://www.formula1.com/en/racing/{year}.html",
                popularity=pop,
                season=year,
                weekend_days=days,
            )
        )
    return races


def calendar_2026() -> list[Race]:  # zachowane dla zgodności wstecznej
    return calendar(2026)


def all_races() -> list[Race]:
    races: list[Race] = []
    for year in SEASONS:
        races.extend(calendar(year))
    return races


def find_races(name: str, seasons: Optional[Iterable[int]] = None) -> list[Race]:
    """Wyścigi o danej nazwie w wybranych sezonach (domyślnie wszystkich)."""
    seasons = set(seasons) if seasons else set(SEASONS)
    return [r for r in all_races() if r.name == name and r.season in seasons]


def race_by_name(name: str, season: Optional[int] = None) -> Optional[Race]:
    """Pojedynczy wyścig po nazwie (najbliższy sezon, jeśli nie podano)."""
    matches = find_races(name, [season] if season else None)
    if not matches:
        return None
    return sorted(matches, key=lambda r: r.season)[0]


def sample_offers_for(
    race: Race,
    source_type: str,
    source_name: str,
    base_currency: str,
    base_url: str,
    price_multiplier: float = 1.0,
) -> list[TicketOffer]:
    """Generuje typowe oferty (trybuny, GA, dodatki) dla danego wyścigu.

    Ceny są przybliżone i przeskalowane ``price_multiplier`` (partnerzy bywają
    drożsi). Dla weekendów 4-dniowych (np. Monaco) ceny weekendowe rosną, a
    etykieta kategorii to „Weekend 4-dniowy". Dla każdego wyścigu dorzucamy
    dodatek Pit Lane Walk.
    """
    m = price_multiplier
    days = race.weekend_days
    weekend_label = f"Weekend {days}-dniowy"
    day_factor = 1.0 if days <= 3 else 1.25  # 4-dniowy droższy

    # (trybuna, kategoria, cena bazowa, jakość 1-10, zadaszenie, notatka, dostępność)
    blueprint = [
        ("General Admission", weekend_label, 110 * day_factor, 3.0, False,
         "Wstęp na tereny ogólne, bez numerowanego miejsca", "dostępne"),
        ("Tribune – łuk", weekend_label, 280 * day_factor, 6.0, False,
         "Dobry widok na zakręt, sporo akcji", "dostępne"),
        ("Tribune – start/meta", weekend_label, 470 * day_factor, 8.5, True,
         "Widok na start, pit-lane i podium, częściowe zadaszenie", "ostatnie"),
        ("Trybuna główna – Premium", weekend_label, 690 * day_factor, 9.5, True,
         "Najlepszy widok, zadaszenie, blisko padoku", "dostępne"),
        ("Tribune – niedziela", "Niedziela (wyścig)", 190, 6.5, False,
         "Tylko dzień wyścigu", "dostępne"),
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

    # Dodatek: Pit Lane Walk (doświadczenie, nie miejsce na trybunie).
    offers.append(
        TicketOffer(
            race_key=race.key,
            source_type=source_type,
            source_name=source_name,
            grandstand="Pit Lane Walk",
            category="Doświadczenie (add-on)",
            price=round(69 * m, 2),
            currency=base_currency,
            seat_quality=5.0,
            covered=False,
            view_notes="Spacer po alei serwisowej (pit lane) przed wyścigiem",
            availability="dostępne",
            buy_url=base_url,
        )
    )
    return offers
