"""GIS parcel boundary and aerial imagery metadata lookup services."""

from datetime import datetime
import json
import re
import urllib.parse
import urllib.request
from typing import Optional

from backend import config


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

    for endpoint in config.PARCEL_ENDPOINTS:
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
