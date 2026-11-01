"""
AI Driver Health Guardian — Geocoding Service
Converts a human-readable address into latitude/longitude using Nominatim (OpenStreetMap).
"""

import time
import requests

# Default fallback coordinates (Perundurai, Tamil Nadu)
DEFAULT_LAT = 11.2720
DEFAULT_LNG = 77.5920

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "HealthGuardianApp/1.0"}


_GEOCODE_CACHE = {}

def geocode_address(address: str) -> tuple:
    """
    Convert a human-readable address string to (latitude, longitude).
    Returns cached result or default Perundurai coordinates instantly.
    """
    if not address:
        return DEFAULT_LAT, DEFAULT_LNG

    cache_key = address.strip().lower()
    if cache_key in _GEOCODE_CACHE:
        return _GEOCODE_CACHE[cache_key]

    try:
        params = {"q": address, "format": "json", "limit": 1}
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=2)
        data = response.json()
        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            _GEOCODE_CACHE[cache_key] = (lat, lng)
            print(f"[Geocoder] '{address}' -> ({lat:.4f}, {lng:.4f})")
            return lat, lng
        else:
            _GEOCODE_CACHE[cache_key] = (DEFAULT_LAT, DEFAULT_LNG)
            return DEFAULT_LAT, DEFAULT_LNG
    except Exception as e:
        _GEOCODE_CACHE[cache_key] = (DEFAULT_LAT, DEFAULT_LNG)
        return DEFAULT_LAT, DEFAULT_LNG


def geocode_address_fallback(address: str):
    """
    Same as geocode_address but returns None if geocoding fails (no fallback).
    """
    try:
        params = {"q": address, "format": "json", "limit": 1}
        time.sleep(1)
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        data = response.json()
        if data and len(data) > 0:
            return float(data[0]["lat"]), float(data[0]["lon"])
        return None
    except Exception:
        return None


if __name__ == "__main__":
    # Quick test
    result = geocode_address("Erode, Tamil Nadu, India")
    print(f"Result: {result}")
