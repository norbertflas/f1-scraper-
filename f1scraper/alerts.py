"""System alertów: powiadom mnie, gdy pojawi się bilet w moim budżecie i jakości.

Przepływ:
  1. definiujesz kryteria (``AlertCriteria``) – np. "Monza, do 400 €, jakość ≥ 8",
  2. ``run_alerts`` scrapuje/wczytuje oferty, dopasowuje je do kryteriów,
  3. nowe trafienia (jeszcze nie zgłoszone) są wysyłane przez wybrany kanał:
     e-mail (SMTP), plik (JSONL) lub konsolę.

Deduplikacja: każda oferta ma "podpis" (wyścig+trybuna+źródło+cena+dostępność)
zapisywany w ``data/alert_state.json``, więc nie dostajesz tego samego alertu
dwa razy. Zmiana ceny/dostępności = nowy podpis = nowy alert.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from .engine import ScrapeResult, load_results, run_scrape

log = logging.getLogger("f1scraper.alerts")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_PATH = DATA_DIR / "alert_state.json"
ALERT_LOG_PATH = DATA_DIR / "alerts.jsonl"


# --------------------------------------------------------------------------
# Kryteria
# --------------------------------------------------------------------------
@dataclass
class AlertCriteria:
    """Pojedynczy "watch" – czego szukasz."""

    name: str = "alert"
    max_price_eur: Optional[float] = None
    min_seat_quality: Optional[float] = None
    country: Optional[str] = None
    source_type: Optional[str] = None  # "circuit" | "partner"
    covered_only: bool = False
    races: list[str] = field(default_factory=list)  # nazwy Race.name; puste = wszystkie

    def to_filters(self) -> dict:
        return dict(
            max_price_eur=self.max_price_eur,
            min_seat_quality=self.min_seat_quality,
            country=self.country,
            source_type=self.source_type,
            covered_only=self.covered_only,
            available_only=True,
        )

    def matches_race(self, race_name: str) -> bool:
        if not self.races:
            return True
        return race_name in self.races

    @classmethod
    def from_dict(cls, d: dict) -> "AlertCriteria":
        return cls(
            name=d.get("name", "alert"),
            max_price_eur=d.get("max_price_eur"),
            min_seat_quality=d.get("min_seat_quality"),
            country=d.get("country"),
            source_type=d.get("source_type"),
            covered_only=bool(d.get("covered_only", False)),
            races=list(d.get("races", [])),
        )


def find_matches(result: ScrapeResult, criteria: AlertCriteria) -> list[dict]:
    """Zwraca oferty pasujące do kryteriów (posortowane wg wartości)."""
    rows = result.ranked_offers(sort_by="value", **criteria.to_filters())
    return [r for r in rows if criteria.matches_race(r["race_name"])]


def offer_signature(row: dict) -> str:
    return "|".join(
        str(row.get(k, ""))
        for k in ("race_key", "grandstand", "source_name", "price_eur", "availability")
    )


# --------------------------------------------------------------------------
# Stan (deduplikacja)
# --------------------------------------------------------------------------
def load_state(path: Path = STATE_PATH) -> set[str]:
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def save_state(seen: set[str], path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# Kanały powiadomień
# --------------------------------------------------------------------------
class Notifier:
    """Interfejs kanału powiadomień."""

    def send(self, subject: str, matches: list[dict]) -> None:  # pragma: no cover
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    def send(self, subject: str, matches: list[dict]) -> None:
        print(f"\n🔔 {subject}")
        print(render_text(matches))


class FileNotifier(Notifier):
    """Dopisuje trafienia do pliku JSONL (łatwe do dalszego przetwarzania)."""

    def __init__(self, path: Path = ALERT_LOG_PATH) -> None:
        self.path = path

    def send(self, subject: str, matches: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            for m in matches:
                fh.write(json.dumps({"subject": subject, **m}, ensure_ascii=False) + "\n")
        log.info("Zapisano %d alertów do %s", len(matches), self.path)


@dataclass
class EmailConfig:
    host: str
    port: int = 587
    user: str = ""
    password: str = ""
    sender: str = ""
    recipient: str = ""
    use_tls: bool = True

    @classmethod
    def from_env(cls, recipient_override: Optional[str] = None) -> Optional["EmailConfig"]:
        """Buduje konfigurację SMTP z ENV.

        Dane logowania (host/user/hasło) ZAWSZE pochodzą ze zmiennych
        środowiskowych – nigdy nie trzymamy ich w repo. Adres odbiorcy może
        przyjść z pliku konfiguracyjnego (``recipient_override``) i ma wtedy
        pierwszeństwo przed ``ALERT_TO``.
        """
        host = os.getenv("SMTP_HOST")
        recipient = recipient_override or os.getenv("ALERT_TO")
        if not host or not recipient:
            return None
        return cls(
            host=host,
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASS", ""),
            sender=os.getenv("ALERT_FROM", os.getenv("SMTP_USER", "")),
            recipient=recipient,
            use_tls=os.getenv("SMTP_TLS", "1") != "0",
        )


class EmailNotifier(Notifier):
    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def send(self, subject: str, matches: list[dict]) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.sender or self.config.user
        msg["To"] = self.config.recipient
        msg.set_content(render_text(matches))
        msg.add_alternative(render_html(matches), subtype="html")

        with smtplib.SMTP(self.config.host, self.config.port) as smtp:
            if self.config.use_tls:
                smtp.starttls()
            if self.config.user:
                smtp.login(self.config.user, self.config.password)
            smtp.send_message(msg)
        log.info("Wysłano e-mail z %d alertami do %s", len(matches), self.config.recipient)


def render_text(matches: list[dict]) -> str:
    lines = []
    for m in matches:
        lines.append(
            f"• {m['race_name']} — {m['grandstand']} ({m['category']}): "
            f"{m['price_eur']:.0f} € | jakość {m['seat_quality']:.1f} | "
            f"wartość {m['value_score']:.1f} | {m['source_name']} | {m['availability']}\n"
            f"  {m.get('buy_url', '')}"
        )
    return "\n".join(lines) if lines else "(brak)"


def render_html(matches: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{m['race_name']}</td><td>{m['grandstand']}</td>"
        f"<td align='right'>{m['price_eur']:.0f} €</td>"
        f"<td align='right'>{m['seat_quality']:.1f}</td>"
        f"<td align='right'>{m['value_score']:.1f}</td>"
        f"<td>{m['source_name']}</td>"
        f"<td><a href='{m.get('buy_url','')}'>Kup</a></td></tr>"
        for m in matches
    )
    return (
        "<h2>🏁 Nowe bilety F1 spełniające Twoje kryteria</h2>"
        "<table border='1' cellpadding='6' cellspacing='0'>"
        "<tr><th>Wyścig</th><th>Trybuna</th><th>Cena</th><th>Jakość</th>"
        "<th>Wartość</th><th>Źródło</th><th></th></tr>"
        f"{rows}</table>"
    )


def default_notifier() -> Notifier:
    """E-mail, jeśli skonfigurowany w ENV; w przeciwnym razie zapis do pliku."""
    cfg = EmailConfig.from_env()
    if cfg:
        return EmailNotifier(cfg)
    log.info("Brak konfiguracji SMTP – alerty trafią do pliku %s", ALERT_LOG_PATH)
    return FileNotifier()


# --------------------------------------------------------------------------
# Główna pętla alertów
# --------------------------------------------------------------------------
def load_config(path: str | Path) -> dict:
    """Wczytuje plik konfiguracyjny i zwraca {'alerts': [...], 'email': {...}}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"alerts": data, "email": {}}
    return {"alerts": data.get("alerts", []), "email": data.get("email", {})}


def load_criteria(path: str | Path) -> list[AlertCriteria]:
    items = load_config(path)["alerts"]
    return [AlertCriteria.from_dict(d) for d in items]


def build_notifier(channel: str, email_settings: Optional[dict] = None) -> Optional[Notifier]:
    """Tworzy kanał powiadomień.

    ``channel``: "auto" | "email" | "file" | "console".
    Adres odbiorcy bierzemy z ``email_settings['to']`` (z pliku konfiguracji),
    a dane SMTP ze zmiennych środowiskowych. Zwraca None, gdy zażądano e-maila,
    a SMTP nie jest skonfigurowany.
    """
    email_settings = email_settings or {}
    recipient = email_settings.get("to")

    if channel == "console":
        return ConsoleNotifier()
    if channel == "file":
        return FileNotifier()
    if channel == "email":
        cfg = EmailConfig.from_env(recipient_override=recipient)
        return EmailNotifier(cfg) if cfg else None
    # auto: e-mail jeśli skonfigurowany, inaczej plik.
    cfg = EmailConfig.from_env(recipient_override=recipient)
    if cfg:
        log.info("Alerty e-mail będą wysyłane na %s", cfg.recipient)
        return EmailNotifier(cfg)
    log.info("Brak konfiguracji SMTP – alerty trafią do pliku %s", ALERT_LOG_PATH)
    return FileNotifier()


def run_alerts(
    criteria_list: list[AlertCriteria],
    notifier: Optional[Notifier] = None,
    *,
    result: Optional[ScrapeResult] = None,
    refresh: bool = True,
    state_path: Path = STATE_PATH,
) -> list[dict]:
    """Dopasowuje oferty do kryteriów i powiadamia o nowych trafieniach.

    Zwraca listę nowych ofert (tych, o których właśnie powiadomiono).
    """
    if result is None:
        result = run_scrape() if refresh else load_results()
    if result is None:
        log.warning("Brak danych do alertów – uruchom najpierw scrapowanie.")
        return []

    notifier = notifier or default_notifier()
    seen = load_state(state_path)

    new_matches: list[dict] = []
    new_signatures: set[str] = set()
    for criteria in criteria_list:
        fresh = []
        for row in find_matches(result, criteria):
            sig = offer_signature(row)
            if sig in seen or sig in new_signatures:
                continue
            new_signatures.add(sig)
            row = {**row, "alert_name": criteria.name}
            fresh.append(row)
        if fresh:
            notifier.send(
                f"F1: {len(fresh)} nowych ofert dla „{criteria.name}”", fresh
            )
            new_matches.extend(fresh)

    if new_signatures:
        save_state(seen | new_signatures, state_path)
    log.info("Alerty: %d nowych trafień", len(new_matches))
    return new_matches
