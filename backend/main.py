import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from services.geocoding import geocode
from services.routing import get_routes
from services.safety import nearby_safety_coverage
from services.safety_routing import generate_route_profiles
from services.sos import dispatch_sos

app = FastAPI(title="HerShield", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class RouteRequest(BaseModel):
    source: str = Field(min_length=2, max_length=150)
    destination: str = Field(min_length=2, max_length=150)

class SOSRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    phone: str = Field(min_length=3, max_length=25)

@app.get("/health")
async def health(): return {"status": "ok"}

@app.post("/sos")
async def send_sos(payload: SOSRequest):
    try:
        result = await dispatch_sos(payload.phone, payload.lat, payload.lng)
        return {"success": True, **result}
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error))

@app.post("/get_safe_route")
async def safe_route(payload: RouteRequest):
    timeout = httpx.Timeout(18.0, connect=6.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            source, destination = await asyncio.gather(geocode(payload.source, client), geocode(payload.destination, client))
            raw_routes = await get_routes(source, destination, client)
            # Gather safety POIs first; they become inputs to individual graph-edge weights.
            all_points = [point for route in raw_routes for point in route["coordinates"]]
            coverage = await nearby_safety_coverage(all_points, client)
            routes = generate_route_profiles(raw_routes, coverage["hospitals"], coverage["police"])
        for route in routes:
            route["duration_s"] = min(item["duration_s"] for item in raw_routes)
        best_route = next(route for route in routes if route["id"] == "safest")
        return {"routes": routes, "best_route": best_route, "source": source, "destination": destination}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Safety services are taking too long. Please try again.")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach the mapping service. Please try again shortly.")
