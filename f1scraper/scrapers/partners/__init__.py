"""Scrapery autoryzowanych partnerów / resellerów biletowych.

UWAGA prawna: wielu partnerów ma w regulaminie (ToS) zakaz automatycznego
pobierania danych oraz silną ochronę anty-bot. Bazowa klasa ``PartnerScraper``
ZAWSZE respektuje robots.txt. Przed włączeniem scrapowania na żywo upewnij się,
że masz do tego prawo (zgoda partnera / program afiliacyjny / publiczne API).

Aby dodać partnera:
  1. Stwórz moduł z klasą dziedziczącą po ``PartnerScraper``.
  2. Ustaw ``name``, ``base_url``, ``currency``, ``covered_races``.
  3. (Opcjonalnie) zaimplementuj ``_parse`` zgodnie z regulaminem partnera.
  4. Zarejestruj klasę w ``f1scraper/registry.py``.
"""
