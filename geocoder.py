import asyncio
import json
import re
import urllib.parse
import urllib.request


def _nominatim_lookup(address: str):
    """Single Nominatim call. Returns (lat, lng) or (None, None)."""
    params = urllib.parse.urlencode({
        "q": address + ", India",
        "format": "json",
        "limit": 1,
        "countrycodes": "in",
        "addressdetails": 0,
    })
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "BillGuard/1.0 (billguard-hackathon)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"[GEOCODE] lookup failed for '{address[:60]}': {e}")
    return None, None


def _build_fallbacks(address: str):
    """
    Build progressively simpler address variants to try in order.

    Strategy:
    1. Full address (cleaned up)
    2. Last N comma-separated tokens (area + city)
    3. Just the city token (last recognisable part)
    """
    # Fix common Gemini OCR artefact: merged words like "PERUNGUDICHENNAI"
    # Insert space before a known city name if it got concatenated
    CITIES = [
        "Chennai", "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad",
        "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow",
        "Kanpur", "Nagpur", "Visakhapatnam", "Indore", "Bhopal", "Patna",
        "Vadodara", "Coimbatore", "Madurai", "Noida", "Gurgaon", "Gurugram",
    ]
    cleaned = address
    for city in CITIES:
        # e.g. "PERUNGUDICHENNAI" → "PERUNGUDI CHENNAI"
        pattern = re.compile(r'([A-Za-z])(' + re.escape(city) + r')', re.IGNORECASE)
        cleaned = pattern.sub(r'\1 \2', cleaned)

    # Remove PIN codes — Nominatim doesn't need them and they can confuse it
    cleaned = re.sub(r'\b\d{6}\b', '', cleaned).strip(', ')

    parts = [p.strip() for p in cleaned.split(',') if p.strip()]

    variants = []
    # 1. Full cleaned address
    variants.append(cleaned)
    # 2. Last 3 parts (area, district, city)
    if len(parts) >= 3:
        variants.append(', '.join(parts[-3:]))
    # 3. Last 2 parts (area + city)
    if len(parts) >= 2:
        variants.append(', '.join(parts[-2:]))
    # 4. Just the last part (city/state)
    if parts:
        variants.append(parts[-1])

    # Deduplicate while preserving order
    seen = set()
    return [v for v in variants if v and not (v in seen or seen.add(v))]


def _geocode_sync(address: str):
    """Tries multiple address simplifications until one geocodes."""
    for variant in _build_fallbacks(address):
        lat, lng = _nominatim_lookup(variant)
        if lat is not None:
            print(f"[GEOCODE] Success with: '{variant[:70]}'")
            return lat, lng
    print(f"[GEOCODE] All variants failed for: '{address[:70]}'")
    return None, None


async def geocode(address: str):
    """Async wrapper — geocodes without blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _geocode_sync, address)
