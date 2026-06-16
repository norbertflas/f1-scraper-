"""Scrapery oficjalnych stron torów.

Aby dodać nowy tor:
  1. Stwórz moduł ``<tor>.py`` z klasą dziedziczącą po ``CircuitScraper``.
  2. Ustaw ``name``, ``race_name``, ``tickets_url``, ``currency``.
  3. (Opcjonalnie) nadpisz ``_parse`` selektorami HTML danej strony.
  4. Zarejestruj klasę w ``f1scraper/registry.py``.
"""
