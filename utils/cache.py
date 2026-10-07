"""Shared cache paths for dynamic source data."""

from pathlib import Path

from utils.config import BASE_DIR


CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
