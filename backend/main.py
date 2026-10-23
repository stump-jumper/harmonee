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

ECOREGION_ENDPOINTS = [
    "https://services.arcgis.com/neT9SoYxizqTHZPH/arcgis/rest/services/EPA_Region_3_Ecoregion_Level_IV/FeatureServer/0/query",
    "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/Level_III_Ecoregions_in_the_US_v1/FeatureServer/0/query",
]

LEVEL_IV_DESCRIPTIONS = {
    "67a": (
        "Broad, gently rolling valleys underlain by fertile limestone and dolomite bedrock "
        "with karst features and spring-fed calcareous streams. Naturally supports rich "
        "mixed oak-hickory and tulip poplar forests alongside calcareous meadow and riparian habitats."
    ),
    "67b": (
        "Rolling valleys and low hills underlain by shale and siltstone with well-drained, "
        "slightly acidic soils. Characterized by dendritic stream drainage and native Appalachian "
        "oak, hickory, and pine woodlands."
    ),
    "67c": (
        "Steep, narrow forested mountain ridges capped by resistant sandstone and conglomerate. "
        "Thin, rocky soils support chestnut oak, red oak, black birch, and pitch pine canopy "
        "with mountain laurel and blueberry understory."
    ),
    "67d": (
        "Dissected ridges, hills, and knobs underlain by interbedded sandstone, chert, and shale. "
        "Supports diverse mixed mesophytic and Appalachian oak-hickory forest communities."
    ),
    "64a": (
        "Undulating plains and low hills underlain by red shale, siltstone, and sandstone. "
        "Supports mixed oak, hickory, ash, and red maple woodlands with warm-water piedmont streams."
    ),
    "64b": (
        "Steep, wooded diabase ridges and boulder-strewn uplands rising above surrounding lowlands. "
        "Thin, rocky soils preserve extensive contiguous oak-hickory and beech-maple forest habitats."
    ),
    "64c": (
        "Rounded hills and incised valleys underlain by metamorphic schists and gneisses. "
        "Naturally vegetated by rich Appalachian oak, tulip poplar, American beech, and hickory "
        "forests with high-gradient piedmont streams."
    ),
    "64d": (
        "Fertile, gently undulating carbonate basins with karst topography and alkaline soils. "
        "Historically supported towering oak-tulip poplar forests and spring-fed limestone meadows."
    ),
    "58h": (
        "Rugged crystalline uplands of Precambrian gneiss and granite separating the Ridge and Valley "
        "from the Piedmont. Features steep wooded slopes, vernal pools, and dense mixed oak, birch, "
        "and tulip poplar canopy."
    ),
}


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


def format_ecoregion_name(name: Optional[str]) -> str:
    if not name:
        return ""
    text = str(name).strip()
    if text.isupper():
        text = text.title().replace("Usa", "USA")
    return text


def describe_level4(l4_code: str, l4_name: str, l3_name: str, l1_name: str) -> str:
    key = (l4_code or "").strip().lower()
    if key in LEVEL_IV_DESCRIPTIONS:
        return LEVEL_IV_DESCRIPTIONS[key]
    if l4_name and l3_name:
        return (
            f"Part of the {l3_name} region within {l1_name or 'temperate North America'}, "
            f"the {l4_name} sub-ecoregion is defined by its local geology, soils, and landform "
            f"relief, shaping native plant communities and wildlife habitat."
        )
    if l3_name:
        return (
            f"Located in the {l3_name} ecoregion, characterized by distinct regional topography, "
            f"soil chemistry, and native woodland and meadow plant assemblages."
        )
    return ""


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


def lookup_ecoregions(lat: float, lon: float) -> Optional[dict]:
    """Query EPA Level I–IV Ecoregion services for all 4 classification levels at (lat, lon)."""
    params = urllib.parse.urlencode(
        {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }
    )
    for endpoint in ECOREGION_ENDPOINTS:
        try:
            url = f"{endpoint}?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "HarmoneeApp/0.1"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                features = payload.get("features", [])
                if not features:
                    continue
                attrs = features[0].get("attributes", {})

                l1_code = attrs.get("NA_L1CODE") or ""
                l1_name = format_ecoregion_name(attrs.get("NA_L1NAME"))

                l2_code = attrs.get("NA_L2CODE") or ""
                l2_name = format_ecoregion_name(attrs.get("NA_L2NAME"))

                l3_code = attrs.get("US_L3CODE") or attrs.get("NA_L3CODE") or ""
                l3_name = format_ecoregion_name(attrs.get("US_L3NAME") or attrs.get("NA_L3NAME"))

                l4_code = attrs.get("US_L4CODE") or ""
                l4_name = format_ecoregion_name(attrs.get("US_L4NAME"))

                result = {
                    "level1": f"{l1_code} {l1_name}".strip() if (l1_code or l1_name) else None,
                    "level2": f"{l2_code} {l2_name}".strip() if (l2_code or l2_name) else None,
                    "level3": f"{l3_code} {l3_name}".strip() if (l3_code or l3_name) else None,
                    "level4": f"{l4_code} {l4_name}".strip() if (l4_code or l4_name) else None,
                    "description": describe_level4(l4_code, l4_name, l3_name, l1_name),
                }
                if any(result.values()):
                    return result
        except Exception:
            continue
    return None


def lookup_parcel_boundary(lat: float, lon: float, address: str = "") -> Optional[dict]:
    """Query GIS parcel polygon services for the property boundary at (lat, lon)."""
    house_match = re.match(r"^\s*(\d+)", address or "")
    house_num = house_match.group(1) if house_match else None

    for endpoint in PARCEL_ENDPOINTS:
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

    ecoregions = data.get("ecoregions")
    if lat is not None and lon is not None and (
        not isinstance(ecoregions, dict) or not ecoregions.get("description")
    ):
        ecoregions = lookup_ecoregions(lat, lon)
        if ecoregions:
            data["ecoregions"] = ecoregions
            dirty = True

    if dirty:
        write_data(data)

    return {
        "address": address,
        "lat": lat,
        "lon": lon,
        "captureDate": capture_date,
        "parcel": parcel,
        "ecoregions": ecoregions,
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
    ecoregions = lookup_ecoregions(lat, lon) if (lat is not None and lon is not None) else None

    data["address"] = cleaned
    data["lat"] = lat
    data["lon"] = lon
    data["captureDate"] = capture_date
    data["parcel"] = parcel
    data["ecoregions"] = ecoregions
    write_data(data)
    return {
        "address": data["address"],
        "lat": data["lat"],
        "lon": data["lon"],
        "captureDate": capture_date,
        "parcel": parcel,
        "ecoregions": ecoregions,
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
