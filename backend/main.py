from datetime import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv(Path(__file__).parent / ".env")

app = FastAPI(title="Harmonee API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).parent / "data.json"
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

PARCEL_ENDPOINTS = [
    "https://mapservices.pasda.psu.edu/server/rest/services/pasda/LehighCounty/MapServer/5/query",
    "https://mapservices.pasda.psu.edu/server/rest/services/pasda/MontgomeryCounty/MapServer/14/query",
]


class AddressPayload(BaseModel):
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None


def read_data() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def write_data(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def lookup_capture_date(lat: float, lon: float) -> Optional[str]:
    """Query aerial/satellite imagery metadata for the capture date at (lat, lon)."""
    try:
        extent = f"{lon - 0.005},{lat - 0.005},{lon + 0.005},{lat + 0.005}"
        params = urllib.parse.urlencode(
            {
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "sr": "4326",
                "layers": "top",
                "tolerance": "1",
                "mapExtent": extent,
                "imageDisplay": "800,600,96",
                "returnGeometry": "false",
                "f": "json",
            }
        )
        url = f"https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/identify?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "HarmoneeApp/0.1"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            for item in payload.get("results", []):
                attrs = item.get("attributes", {})
                raw_ymd = attrs.get("DATE (YYYYMMDD)") or attrs.get("SRC_DATE")
                if raw_ymd and raw_ymd != "Null" and len(str(raw_ymd)) == 8:
                    dt = datetime.strptime(str(raw_ymd), "%Y%m%d")
                    return dt.strftime("%b %d, %Y")
                src_date2 = attrs.get("SRC_DATE2")
                if src_date2 and src_date2 != "Null":
                    return str(src_date2)
    except Exception:
        pass
    return None


def lookup_parcel_boundary(lat: float, lon: float, address: str = "") -> Optional[dict]:
    """Query GIS parcel polygon services for the property boundary at (lat, lon)."""
    house_match = re.match(r"^\s*(\d+)", address or "")
    house_num = house_match.group(1) if house_match else None

    for endpoint in PARCEL_ENDPOINTS:
        # 1. Try exact point-in-polygon intersection first
        for distance in (0, 35):
            try:
                query_params = {
                    "geometry": f"{lon},{lat}",
                    "geometryType": "esriGeometryPoint",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": "*",
                    "outSR": "4326",
                    "f": "geojson",
                }
                if distance > 0:
                    query_params["distance"] = str(distance)
                    query_params["units"] = "esriSRUnit_Meter"

                url = f"{endpoint}?{urllib.parse.urlencode(query_params)}"
                req = urllib.request.Request(url, headers={"User-Agent": "HarmoneeApp/0.1"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    geojson = json.loads(resp.read().decode("utf-8"))
                    features = geojson.get("features", [])
                    if not features:
                        continue

                    if len(features) == 1 or not house_num:
                        return features[0]

                    for feat in features:
                        props_str = json.dumps(feat.get("properties", {}))
                        if f'"{house_num}"' in props_str or f'"{house_num} ' in props_str:
                            return feat
                    return features[0]
            except Exception:
                continue
    return None


def format_photon_feature(feature: dict) -> Optional[dict]:
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    housenumber = props.get("housenumber", "")
    street = props.get("street") or props.get("name") or ""
    city = props.get("city") or props.get("town") or props.get("village") or props.get("locality") or ""
    state = props.get("state", "")
    postcode = props.get("postcode", "")
    country = props.get("country", "")

    street_line = f"{housenumber} {street}".strip()
    parts = [p for p in [street_line, city, state, postcode, country] if p]
    if not parts:
        return None

    label = ", ".join(parts)
    lon = coords[0] if len(coords) >= 2 else None
    lat = coords[1] if len(coords) >= 2 else None
    return {"label": label, "lat": lat, "lon": lon}


def lookup_suggestions(query: str) -> list[dict]:
    suggestions = []
    seen = set()

    # 1. Try Mapbox Geocoding API if token is configured
    if MAPBOX_TOKEN:
        try:
            encoded_q = urllib.parse.quote(query)
            params = urllib.parse.urlencode(
                {
                    "access_token": MAPBOX_TOKEN,
                    "autocomplete": "true",
                    "types": "address,place,postcode",
                    "limit": 5,
                }
            )
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_q}.json?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "HarmoneeApp/0.1"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for feat in payload.get("features", []):
                    label = feat.get("place_name")
                    center = feat.get("center", [])
                    if label and label not in seen and len(center) >= 2:
                        seen.add(label)
                        suggestions.append(
                            {"label": label, "lon": center[0], "lat": center[1]}
                        )
        except Exception:
            pass

    # 2. Fallback to Photon (OpenStreetMap search-as-you-type geocoder)
    if not suggestions:
        try:
            params = urllib.parse.urlencode({"q": query, "limit": 6, "lang": "en"})
            req = urllib.request.Request(
                f"https://photon.komoot.io/api/?{params}",
                headers={"User-Agent": "HarmoneeApp/0.1 (local-dev)"},
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for feat in payload.get("features", []):
                    item = format_photon_feature(feat)
                    if item and item["label"] not in seen:
                        seen.add(item["label"])
                        suggestions.append(item)
        except Exception:
            pass

    return suggestions[:5]


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/address")
def get_address():
    data = read_data()
    address = data.get("address", "")
    lat = data.get("lat")
    lon = data.get("lon")
    dirty = False

    if address and (lat is None or lon is None):
        matches = lookup_suggestions(address)
        if matches:
            lat = matches[0].get("lat")
            lon = matches[0].get("lon")
            data["lat"] = lat
            data["lon"] = lon
            dirty = True

    capture_date = data.get("captureDate")
    if lat is not None and lon is not None and not capture_date:
        capture_date = lookup_capture_date(lat, lon)
        if capture_date:
            data["captureDate"] = capture_date
            dirty = True

    parcel = data.get("parcel")
    if lat is not None and lon is not None and not parcel:
        parcel = lookup_parcel_boundary(lat, lon, address)
        if parcel:
            data["parcel"] = parcel
            dirty = True

    if dirty:
        write_data(data)

    return {
        "address": address,
        "lat": lat,
        "lon": lon,
        "captureDate": capture_date,
        "parcel": parcel,
    }


@app.post("/api/address")
def save_address(payload: AddressPayload):
    data = read_data()
    cleaned = payload.address.strip()
    lat = payload.lat
    lon = payload.lon

    if cleaned and (lat is None or lon is None):
        matches = lookup_suggestions(cleaned)
        if matches:
            lat = matches[0].get("lat")
            lon = matches[0].get("lon")

    capture_date = lookup_capture_date(lat, lon) if (lat is not None and lon is not None) else None
    parcel = lookup_parcel_boundary(lat, lon, cleaned) if (lat is not None and lon is not None) else None

    data["address"] = cleaned
    data["lat"] = lat
    data["lon"] = lon
    data["captureDate"] = capture_date
    data["parcel"] = parcel
    write_data(data)
    return {
        "address": data["address"],
        "lat": data["lat"],
        "lon": data["lon"],
        "captureDate": capture_date,
        "parcel": parcel,
        "saved": True,
    }


@app.get("/api/imagery-date")
def get_imagery_date(lat: float = Query(...), lon: float = Query(...)):
    return {"captureDate": lookup_capture_date(lat, lon)}


@app.get("/api/address/autocomplete")
def autocomplete_address(q: str = Query("", min_length=1)):
    query = q.strip()
    if len(query) < 3:
        return {"suggestions": []}
    return {"suggestions": lookup_suggestions(query)}
