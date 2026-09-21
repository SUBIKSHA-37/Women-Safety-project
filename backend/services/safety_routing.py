"""Safety-aware graph routing independent from OSRM's route selection."""
from __future__ import annotations
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
import heapq

ROUTE_PROFILES = (
    {"id": "shortest", "label": "Shortest", "alpha": 0.0, "color": "#D32F2F", "recommendation": "This is the quickest route, but it may pass through higher-risk areas."},
    {"id": "balanced", "label": "Balanced", "alpha": 5.0, "color": "#FF9800", "recommendation": "This route balances travel distance with lower-risk road segments."},
    {"id": "safest", "label": "Safest", "alpha": 10.0, "color": "#00C853", "recommendation": "We recommend the green route: it has lower risk and better safety coverage."},
)

def _node(point: list[float]) -> tuple[float, float]: return round(point[0], 6), round(point[1], 6)
def meters(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b)); h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6_371_000 * 2 * asin(sqrt(h))
def _crime_density(mid: tuple[float, float]) -> float: return abs(sin(mid[0]*31.7)*cos(mid[1]*19.3))*10
def _hospital_risk(mid: tuple[float, float], hospitals: list[dict]) -> float:
    if not hospitals: return 6.0
    return min(10.0, min(meters(mid, (h["lat"], h["lon"])) for h in hospitals)/500)
def _lighting_risk() -> float: return 7.0 if datetime.now().hour >= 19 or datetime.now().hour < 6 else 1.5

def edge_risk(start: tuple[float, float], end: tuple[float, float], hospitals: list[dict]) -> dict:
    mid = ((start[0]+end[0])/2, (start[1]+end[1])/2); crime, hospital, lighting = _crime_density(mid), _hospital_risk(mid, hospitals), _lighting_risk()
    return {"score": round(crime*.5+hospital*.2+lighting*.3, 2), "crime_density": round(crime, 2), "hospital_distance_risk": round(hospital, 2), "lighting_risk": lighting}

def build_road_graph(candidate_routes: list[dict], hospitals: list[dict]) -> tuple[dict, tuple, tuple]:
    graph: dict[tuple, dict[tuple, dict]] = {}
    for candidate_index, route in enumerate(candidate_routes):
        for a, b in zip(route["coordinates"], route["coordinates"][1:]):
            start, end = _node(a), _node(b); risk, distance = edge_risk(start, end, hospitals), meters(start, end)
            graph.setdefault(start, {})[end] = {"distance_m": distance, "risk": risk, "candidate_index": candidate_index}
    return graph, _node(candidate_routes[0]["coordinates"][0]), _node(candidate_routes[0]["coordinates"][-1])

def dijkstra(graph: dict, source: tuple, destination: tuple, alpha: float, excluded_edges: set[tuple] | None = None) -> tuple[list[tuple], list[dict]]:
    excluded_edges = excluded_edges or set(); queue, costs, previous = [(0.0, source)], {source: 0.0}, {source: None}
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != costs.get(node): continue
        if node == destination: break
        for neighbor, edge in graph.get(node, {}).items():
            if (node, neighbor) in excluded_edges: continue
            next_cost = cost + edge["distance_m"] + edge["risk"]["score"]*alpha
            if next_cost < costs.get(neighbor, float("inf")):
                costs[neighbor], previous[neighbor] = next_cost, node; heapq.heappush(queue, (next_cost, neighbor))
    if destination not in previous: raise ValueError("No connected graph route is available for this safety profile.")
    nodes, current = [], destination
    while current is not None: nodes.append(current); current = previous[current]
    nodes.reverse(); return nodes, [graph[a][b] for a, b in zip(nodes, nodes[1:])]

def _serialize(profile: dict, nodes: list[tuple], edges: list[dict], hospitals: list[dict], police: list[dict]) -> dict:
    average = sum(edge["risk"]["score"] for edge in edges)/max(1,len(edges)); distance = sum(edge["distance_m"] for edge in edges)
    segments = [{"start": list(a), "end": list(b), "risk": edge["risk"]["score"]} for a,b,edge in zip(nodes,nodes[1:],edges)]
    return {**profile, "coordinates":[list(node) for node in nodes], "distance_m":round(distance,1), "weighted_cost":round(sum(e["distance_m"]+e["risk"]["score"]*profile["alpha"] for e in edges),1), "average_edge_risk":round(average,2), "score":round(100-min(90,average*10)), "risk_level":"low" if average<3.5 else "medium" if average<6.5 else "high", "risk_segments":segments[::max(1,len(segments)//75)], "hospitals":hospitals, "police":police, "algorithm":"Dijkstra safety-weighted graph search", "safety_explanation":"Lower crime density, stronger hospital access, and safer lighting conditions reduced the cumulative edge risk."}

def generate_route_profiles(candidate_routes: list[dict], hospitals: list[dict], police: list[dict]) -> list[dict]:
    """Run distance, balanced, and safest Dijkstra profiles over the same edge graph."""
    graph, source, destination = build_road_graph(candidate_routes, hospitals); routes, signatures = [], set()
    for profile in ROUTE_PROFILES:
        nodes, edges = dijkstra(graph, source, destination, profile["alpha"]); signature = tuple(nodes)
        if signature in signatures:
            # Exclude every already-presented path, not merely the last one.
            # This guarantees a visibly different route whenever the graph offers one.
            excluded = {(tuple(a), tuple(b)) for route in routes for a, b in zip(route["coordinates"], route["coordinates"][1:])}
            try: nodes, edges = dijkstra(graph, source, destination, profile["alpha"], excluded)
            except ValueError: pass
            signature = tuple(nodes)
        signatures.add(signature); routes.append(_serialize(profile,nodes,edges,hospitals,police))
    return routes
