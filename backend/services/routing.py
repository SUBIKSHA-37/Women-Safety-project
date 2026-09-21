import httpx

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

async def get_routes(source: dict, destination: dict, client: httpx.AsyncClient) -> list[dict]:
    """Get alternate driving routes in GeoJSON coordinate format from OSRM."""
    coordinates = f"{source['lon']},{source['lat']};{destination['lon']},{destination['lat']}"
    response = await client.get(
        f"{OSRM_URL}/{coordinates}",
        params={"alternatives": "3", "overview": "full", "geometries": "geojson", "steps": "false"},
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("No drivable route was found for these locations.")
    return [
        {"coordinates": [[lat, lon] for lon, lat in route["geometry"]["coordinates"]], "distance_m": route["distance"], "duration_s": route["duration"]}
        for route in data["routes"]
    ]
