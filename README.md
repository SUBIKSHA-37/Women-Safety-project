# Nila Safe

A safety-first intelligent routing experience for women travellers. OSRM supplies candidate road geometries, while the backend builds a directed road-segment graph and runs Dijkstra to select the lowest safety-weighted path.

## Stack

- Frontend: React, Vite, Tailwind CSS, Leaflet / React Leaflet, Lucide icons
- Backend: FastAPI, HTTPX
- Mapping services: Nominatim, OSRM, Overpass

## Run locally

Open two terminals.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). Permit browser location access to activate live tracking and SOS location sharing. The FastAPI docs are at `http://localhost:8000/docs`.

## Configure real SOS SMS delivery

The app uses a mock response by default, so it cannot accidentally message anyone during development. To deliver real alerts, create `backend/.env` from `backend/.env.example`, enter your Twilio details, and verify the recipient numbers (required on a Twilio trial account). The backend automatically loads this file on startup.

```powershell
uvicorn main:app --reload --port 8000
```

The saved emergency contact accepts `7550397115`, `917550397115`, or `+917550397115` and is normalized to `+917550397115` before Twilio is called. `POLICE_EMERGENCY_PHONE` is optional; if omitted or invalid, it is skipped so it never prevents delivery to the saved emergency contact. The emergency short code `100` is not a valid Twilio SMS recipient. Pressing SOS retrieves a fresh browser location and posts it with the locally saved contact to `/sos`.

## Deployment

- **Frontend (Vercel)**: The frontend is a static Vite app. In the Vercel dashboard/import flow, set the root to `frontend` and the build command to `npm run vercel-build`. Set the output directory to `dist`. Add an environment variable `VITE_API_URL=https://<your-backend-service>`.

- **Backend (Render)**: The backend is a Python FastAPI app. On Render, create a new Web Service from this repo's `backend` directory. Use the `Dockerfile` provided or the `gunicorn` start command via the `Procfile`. Ensure `ALLOWED_ORIGINS` includes your deployed frontend domain (e.g., `https://your-frontend.vercel.app`). Add Twilio environment variables from `backend/.env.example`.

Example `VITE_API_URL` for frontend environment variables: `https://your-backend.onrender.com`

After deploying both services, update `ALLOWED_ORIGINS` and `VITE_API_URL` to match the production domains.

## Safety scoring

The backend returns three genuinely separate Dijkstra profiles over the road-edge graph:

- `Shortest` (red): `alpha = 0`
- `Balanced` (orange): `alpha = 5`
- `Safest` (green, recommended): `alpha = 10`

Each road segment uses the explicit routing weight:

`edge_weight = distance_m + (edge_risk × alpha)`

`alpha` defaults to `8` and can be tuned in `backend/services/safety_routing.py`. The current `edge_risk` blends a deterministic mock crime-density signal (45%), distance-to-hospital risk (35%), and a mock day/night lighting risk (20%). Replace the mock providers with validated municipal feeds when available.

The backend samples every tenth route coordinate for efficiency, queries hospital coverage, constructs a road-edge graph from candidate geometry, and runs weighted Dijkstra. The selected `best_route` includes `average_edge_risk`, `weighted_cost`, `algorithm`, and an explanation for the frontend. Nominatim and OSRM failures produce clear API errors; Overpass coverage failures degrade gracefully with a conservative hospital-risk fallback.
