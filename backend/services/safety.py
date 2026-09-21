import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RISK_PENALTIES = {"chennai": 3, "kallakurichi": 2, "thanjavur": 2, "madurai": 1, "coimbatore": 1}

def city_penalty(*places: str) -> int:
    phrase = " ".join(places).lower()
    return next((penalty for city, penalty in RISK_PENALTIES.items() if city in phrase), 2)

async def nearby_safety_coverage(points: list[list[float]], client: httpx.AsyncClient) -> dict:
    """Query nearby police and hospitals around a sparse set of route points."""
    # Sample every tenth point, then spread the bounded query set across the journey.
    every_tenth = points[::10]
    stride = max(1, len(every_tenth) // 18)
    sampled = every_tenth[::stride][:18]
    if not sampled:
        return {"police": [], "hospitals": []}
    nodes = "".join(f"node(around:350,{lat},{lon})[amenity~\"police|hospital\"];" for lat, lon in sampled)
    query = f"[out:json][timeout:12];({nodes});out center;"
    try:
        response = await client.post(OVERPASS_URL, content=query, headers={"Content-Type": "text/plain"})
        response.raise_for_status()
        seen, police, hospitals = set(), [], []
        for item in response.json().get("elements", []):
            key = item.get("id")
            if key in seen: continue
            seen.add(key)
            target = police if item.get("tags", {}).get("amenity") == "police" else hospitals
            target.append({"lat": item.get("lat", item.get("center", {}).get("lat")), "lon": item.get("lon", item.get("center", {}).get("lon")), "name": item.get("tags", {}).get("name", "Nearby safety service")})
        return {"police": police[:12], "hospitals": hospitals[:12]}
    except (httpx.HTTPError, ValueError):
        return {"police": [], "hospitals": []}

async def score_route(route: dict, source: str, destination: str, client: httpx.AsyncClient) -> dict:
    coverage = await nearby_safety_coverage(route["coordinates"], client)
    police_count, hospital_count = len(coverage["police"]), len(coverage["hospitals"])
    score = police_count * 3 + hospital_count * 2 - city_penalty(source, destination)
    return {**route, **coverage, "score": score, "risk_level": "low" if score >= 8 else "medium" if score >= 3 else "high"}
