import asyncio
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.geocoding import geocode
from services.routing import get_routes
from services.safety import nearby_safety_coverage
from services.safety_routing import generate_route_profiles
from services.sos import dispatch_sos

# -------------------- APP INIT -------------------- #
app = FastAPI(title="HerShield", version="1.0.0")

# -------------------- CORS FIX (FINAL) -------------------- #
# Allow all origins (safe for now, fixes your issue completely)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://womensaferout.vercel.app"],          # ✅ allow all
    allow_credentials=False,      # ✅ must be False with "*"
    allow_methods=["*"],          # ✅ allow all methods (POST, GET, OPTIONS)
    allow_headers=["*"],          # ✅ allow all headers
)

# -------------------- MODELS -------------------- #
class RouteRequest(BaseModel):
    source: str = Field(min_length=2, max_length=150)
    destination: str = Field(min_length=2, max_length=150)

class SOSRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    phone: str = Field(min_length=3, max_length=25)

# -------------------- HEALTH ROUTES -------------------- #
@app.get("/")
async def root():
    return {"message": "HerShield API running 🚀"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# -------------------- SOS API -------------------- #
@app.post("/sos")
async def send_sos(payload: SOSRequest):
    try:
        result = await dispatch_sos(payload.phone, payload.lat, payload.lng)
        return {"success": True, **result}
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=str(error))

# -------------------- SAFE ROUTE API -------------------- #
@app.post("/get_safe_route")
async def safe_route(payload: RouteRequest):
    timeout = httpx.Timeout(18.0, connect=6.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:

            # Step 1: Geocode
            source, destination = await asyncio.gather(
                geocode(payload.source, client),
                geocode(payload.destination, client)
            )

            # Step 2: Routing
            raw_routes = await get_routes(source, destination, client)

            # Step 3: Collect points
            all_points = [
                point for route in raw_routes for point in route["coordinates"]
            ]

            # Step 4: Safety coverage
            coverage = await nearby_safety_coverage(all_points, client)

            # Step 5: Generate profiles
            routes = generate_route_profiles(
                raw_routes,
                coverage["hospitals"],
                coverage["police"]
            )

        # Step 6: Assign duration
        min_duration = min(item["duration_s"] for item in raw_routes)
        for route in routes:
            route["duration_s"] = min_duration

        # Step 7: Pick safest
        best_route = next(
            (route for route in routes if route["id"] == "safest"),
            routes[0]
        )

        return {
            "routes": routes,
            "best_route": best_route,
            "source": source,
            "destination": destination
        }

    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Safety services are taking too long. Please try again."
        )

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Could not reach the mapping service."
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(error)}"
        )

# -------------------- LOCAL RUN -------------------- #
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)