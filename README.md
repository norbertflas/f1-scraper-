# 🏁 F1 Ticket Scraper

Wyszukiwarka biletów na wyścigi **Formuły 1**. Przeszukuje oficjalny kalendarz
F1, strony torów oraz autoryzowanych partnerów biletowych, a następnie **ocenia
oferty** pod kątem stosunku jakości miejsca do ceny — żebyś szybko znalazł dobry
wyścig, na dobrej trybunie, w dobrej cenie.

Wyniki przeglądasz w **dashboardzie webowym** (filtry: cena, jakość miejsca,
kraj, źródło, zadaszenie) albo z linii poleceń.

## Szybki start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Zescrapuj źródła i zapisz wyniki
python -m f1scraper.cli refresh

# 2a) Dashboard webowy:
python app.py            # http://127.0.0.1:5000

# 2b) ...albo w terminalu:
python -m f1scraper.cli top --max-price 400 --sort value --best-per-race
```

## Jak liczona jest „wartość”

Każda oferta dostaje `value_score`:

```
wartość = (jakość_miejsca × atrakcyjność_wyścigu) ÷ cena_w_EUR
```

- **jakość_miejsca** (1–10) — widok na start/metę, zadaszenie, bliskość padoku,
- **atrakcyjność_wyścigu** (1–5) — popularność danego Grand Prix,
- **cena** — przeliczana do EUR (kursy przybliżone, patrz `models.FX_TO_EUR`).

Oferty wyprzedane mają wartość 0; „ostatnie sztuki” są lekko karane.

## Źródła danych

| Typ | Przykłady | Status |
|-----|-----------|--------|
| `calendar` | formula1.com | kalendarz sezonu |
| `circuit` | Monza, Silverstone, Spa | strony torów |
| `partner` | GooTickets, F1 Experiences | autoryzowani resellerzy |

Strony F1 i partnerów są chronione anty-botem, a ich HTML zmienia się co sezon.
Dlatego każdy scraper najpierw **próbuje pobrać dane na żywo**, a gdy się nie
uda (403 / brak sieci / zmiana układu), korzysta z **wbudowanych danych
zapasowych** (`f1scraper/data_fallback.py`) — dzięki temu dashboard zawsze coś
pokazuje, a strukturę danych łatwo porównać.

### „Dobry obywatel sieci”

`f1scraper/fetch.py` (`PoliteFetcher`):
- respektuje **robots.txt** (można wyłączyć `--no-robots` na własną odpowiedzialność),
- ogranicza tempo zapytań (rate limit per domena),
- cache'uje odpowiedzi na dysku (`data/http_cache/`),
- przedstawia się czytelnym User-Agentem.

> ⚠️ **Uwaga prawna:** wielu partnerów ma w regulaminie zakaz scrapowania.
> Przed włączeniem pobierania na żywo upewnij się, że masz do tego prawo
> (zgoda / program afiliacyjny / publiczne API).

## Architektura

```
app.py                      # dashboard Flask
f1scraper/
├── models.py               # Race, TicketOffer, ranking (value_score)
├── fetch.py                # PoliteFetcher (robots.txt, rate limit, cache)
├── engine.py               # uruchamia scrapery, scala dane, filtruje/sortuje
├── registry.py             # lista aktywnych scraperów  ← tu dodajesz nowe
├── cli.py                  # interfejs wiersza poleceń
├── data_fallback.py        # kalendarz 2026 + przykładowe oferty
└── scrapers/
    ├── base.py             # BaseScraper (wspólny interfejs)
    ├── f1_calendar.py      # oficjalny kalendarz F1
    ├── circuits/           # scrapery torów (base_circuit + per-tor)
    └── partners/           # scrapery partnerów (base_partner + per-partner)
templates/index.html        # widok dashboardu
static/style.css
tests/                      # testy (działają offline)
```

### Dodanie nowego toru

1. Utwórz `f1scraper/scrapers/circuits/<tor>.py` z klasą po `CircuitScraper`
   (ustaw `name`, `race_name`, `tickets_url`, `currency`).
2. Opcjonalnie nadpisz `_parse(html)` selektorami danej strony.
3. Zarejestruj klasę w `f1scraper/registry.py`.

(Analogicznie dla partnera — `PartnerScraper`.)

## CLI

```bash
python -m f1scraper.cli refresh [--no-robots] [--no-cache]
python -m f1scraper.cli top [--max-price N] [--min-quality N] [--country X]
                            [--source circuit|partner] [--covered]
                            [--sort value|price|quality|date] [--limit N]
                            [--best-per-race]
```

## Testy

```bash
python -m pytest tests/ -q
```
