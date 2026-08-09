"""Google Places (New) — entity resolution and recommendations."""
from __future__ import annotations

import httpx

from app import config

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join(
    f"places.{f}"
    for f in [
        "id",
        "displayName",
        "formattedAddress",
        "location",
        "types",
        "rating",
        "userRatingCount",
        "googleMapsUri",
    ]
)


def _post(payload: dict, max_results: int) -> list[dict]:
    if not config.GOOGLE_PLACES_API_KEY:
        return []
    headers = {
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": FIELDS,
    }
    payload["maxResultCount"] = max_results
    r = httpx.post(SEARCH_URL, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    out = []
    for p in r.json().get("places", []):
        out.append(
            {
                "place_id": p.get("id"),
                "name": (p.get("displayName") or {}).get("text"),
                "address": p.get("formattedAddress"),
                "lat": (p.get("location") or {}).get("latitude"),
                "lon": (p.get("location") or {}).get("longitude"),
                "category": (p.get("types") or [None])[0],
                "rating": p.get("rating"),
                "rating_count": p.get("userRatingCount"),
                "maps_url": p.get("googleMapsUri"),
            }
        )
    return out


def resolve(name_hint: str, lat: float | None, lon: float | None) -> dict | None:
    """Best candidate for 'the place the user just mentioned', biased to GPS."""
    payload: dict = {"textQuery": name_hint}
    if lat is not None and lon is not None:
        payload["locationBias"] = {
            "circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 2000.0}
        }
    results = _post(payload, max_results=1)
    return results[0] if results else None


def recommend(query: str, lat: float | None, lon: float | None, n: int = 3) -> list[dict]:
    payload: dict = {"textQuery": query}
    if lat is not None and lon is not None:
        payload["locationBias"] = {
            "circle": {"center": {"latitude": lat, "longitude": lon}, "radius": 3000.0}
        }
    return _post(payload, max_results=n)
