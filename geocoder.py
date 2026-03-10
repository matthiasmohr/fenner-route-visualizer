"""
Geocoding module: static JSON cache + Nominatim fallback.

Cache format: { "address string": [lat, lon] }  or  { "address string": null }
null means geocoding was attempted but failed – won't be retried until cache is cleared.
"""

import json
import time
from pathlib import Path

import requests
import streamlit as st

import config


# ─────────────────────────────────────────────────────────────────────────────
# Cache I/O
# ─────────────────────────────────────────────────────────────────────────────

def load_cache() -> dict:
    cache_file = Path(config.GEOCODE_CACHE_FILE)
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(config.GEOCODE_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False, sort_keys=True)


# ─────────────────────────────────────────────────────────────────────────────
# Address building
# ─────────────────────────────────────────────────────────────────────────────

def _clean_plz(plz: str) -> str:
    """Strip country prefixes like 'D-', 'A-', 'CH-' from postal codes."""
    for prefix in ("D-", "A-", "CH-", "d-", "a-", "ch-"):
        if plz.startswith(prefix):
            return plz[len(prefix):]
    return plz


def build_address(row: dict) -> str:
    """Build a geocodable address string from a sheet row."""
    street = str(row.get(config.COL_STREET, "")).strip()
    plz = _clean_plz(str(row.get(config.COL_PLZ, "")).strip())
    city = str(row.get(config.COL_CITY, "")).strip()
    parts = [p for p in [street, plz, city] if p]
    return ", ".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Nominatim geocoding
# ─────────────────────────────────────────────────────────────────────────────

def geocode_one(address: str) -> list | None:
    """Query Nominatim for a single address. Returns [lat, lon] or None."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "de,at,ch",
            },
            headers={"User-Agent": config.NOMINATIM_USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return [float(results[0]["lat"]), float(results[0]["lon"])]
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Batch geocoding
# ─────────────────────────────────────────────────────────────────────────────

def geocode_dataframe(df, force_refresh: bool = False):
    """
    Add 'lat' and 'lon' columns to df using the cache + Nominatim fallback.

    Returns (df_with_coords, cache_dict).
    Shows a progress bar in Streamlit for newly geocoded addresses.
    """
    import pandas as pd

    cache = {} if force_refresh else load_cache()

    # Build address list for every row
    addresses = [build_address(row) for _, row in df.iterrows()]

    # Find unique addresses not yet in cache (exclude empty strings)
    new_addresses = sorted({a for a in addresses if a and a not in cache})

    if new_addresses:
        progress_bar = st.progress(
            0.0,
            text=f"Geocoding {len(new_addresses)} neue Adressen via Nominatim…",
        )
        for i, address in enumerate(new_addresses):
            result = geocode_one(address)
            cache[address] = result  # None if failed
            save_cache(cache)  # save after every address (resilience)
            time.sleep(config.NOMINATIM_DELAY)
            progress_bar.progress(
                (i + 1) / len(new_addresses),
                text=f"Geocoding {i + 1}/{len(new_addresses)}: {address[:55]}…",
            )
        progress_bar.empty()

    # Apply coordinates to dataframe
    df = df.copy()
    df["_addr"] = addresses
    df["lat"] = df["_addr"].map(lambda a: cache[a][0] if cache.get(a) else None)
    df["lon"] = df["_addr"].map(lambda a: cache[a][1] if cache.get(a) else None)
    df = df.drop(columns=["_addr"])

    return df, cache
