import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/address")
def get_address():
    data = read_data()
    return {
        "address": data.get("address", ""),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
    }


@app.post("/api/address")
def save_address(payload: AddressPayload):
    data = read_data()
    data["address"] = payload.address.strip()
    data["lat"] = payload.lat
    data["lon"] = payload.lon
    write_data(data)
    return {
        "address": data["address"],
        "lat": data["lat"],
        "lon": data["lon"],
        "saved": True,
    }


@app.get("/api/address/autocomplete")
def autocomplete_address(q: str = Query("", min_length=1)):
    query = q.strip()
    if len(query) < 3:
        return {"suggestions": []}

    suggestions = []
    seen = set()

    # 1. Try Photon (OpenStreetMap search-as-you-type geocoder)
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

    # 2. Fallback to OpenStreetMap Nominatim if Photon returned nothing
    if not suggestions:
        try:
            params = urllib.parse.urlencode(
                {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 5}
            )
            req = urllib.request.Request(
                f"https://nominatim.openstreetmap.org/search?{params}",
                headers={"User-Agent": "HarmoneeApp/0.1 (local-dev)"},
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                items = json.loads(resp.read().decode("utf-8"))
                for it in items:
                    label = it.get("display_name")
                    if label and label not in seen:
                        seen.add(label)
                        suggestions.append(
                            {
                                "label": label,
                                "lat": float(it["lat"]) if "lat" in it else None,
                                "lon": float(it["lon"]) if "lon" in it else None,
                            }
                        )
        except Exception:
            pass

    return {"suggestions": suggestions[:5]}
