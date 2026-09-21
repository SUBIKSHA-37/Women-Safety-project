import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

async def geocode(place: str, client: httpx.AsyncClient) -> dict:
    """Resolve a place name to a latitude/longitude using OpenStreetMap."""
    try:
        response = await client.get(
            NOMINATIM_URL,
            params={"q": place, "format": "jsonv2", "limit": 1, "countrycodes": "in"},
            headers={"User-Agent": "NilaSafe/1.0 (safety routing demo)"},
        )
        response.raise_for_status()
        results = response.json()
        if results:
            return {"lat": float(results[0]["lat"]), "lon": float(results[0]["lon"]), "label": results[0]["display_name"]}
    except (httpx.HTTPError, ValueError, KeyError):
        pass
    raise ValueError(f"Could not find '{place}'. Try a more specific place name.")
