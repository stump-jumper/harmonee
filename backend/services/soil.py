"""USDA Web Soil Survey and Soil Data Access (SDA) service.

Fetches SSURGO soil map unit polygons and metadata using the property parcel bounds as
the Area of Interest (AOI). Calculates property coverage percentages and polygon centroids
for map unit symbols.
"""

import json
from typing import Optional
import urllib.parse
import urllib.request

from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely import wkt

from backend import config

SOIL_PALETTE = [
    "#c28b5e",  # Terra cotta / rich loam
    "#8b7355",  # Silt loam
    "#d4a373",  # Sand / sandy loam
    "#a3b18a",  # Prairie / sage loam
    "#606c38",  # Dark forest loam
    "#e09f3e",  # Amber loess
    "#99582a",  # Clay rust
    "#7f5539",  # Deep peat / umber
    "#b08968",  # Alluvium
    "#b7b7a4",  # Calcareous / limestone
]


def build_aoi_wkt(minx: float, miny: float, maxx: float, maxy: float) -> str:
    """Format bounding box as a closed WKT POLYGON for USDA SDA spatial queries."""
    return f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"


def query_sda_soil_mapunits(aoi_wkt: str, timeout: int = 12) -> list[dict]:
    """Execute SQL query against USDA Soil Data Access (SDA) post.rest endpoint."""
    query = f"""
SELECT
    m.mukey,
    m.musym,
    m.muname,
    p.mupolygongeo.STIntersection(geometry::STGeomFromText('{aoi_wkt}', 4326)).STAsText() AS geom_wkt
FROM mupolygon p
JOIN mapunit m ON p.mukey = m.mukey
WHERE p.mupolygongeo.STIntersects(geometry::STGeomFromText('{aoi_wkt}', 4326)) = 1
"""
    payload = json.dumps({"format": "JSON+COLUMNNAME", "query": query}).encode("utf-8")
    req = urllib.request.Request(
        getattr(config, "USDA_SDA_REST_URL", "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "HarmoneeApp/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    rows = result.get("Table", [])
    if not rows or len(rows) < 2:
        return []

    headers = [str(h).lower() for h in rows[0]]
    try:
        idx_mukey = headers.index("mukey")
        idx_musym = headers.index("musym")
        idx_muname = headers.index("muname")
        idx_wkt = headers.index("geom_wkt")
    except ValueError:
        return []

    records = []
    for r in rows[1:]:
        if len(r) > max(idx_mukey, idx_musym, idx_muname, idx_wkt):
            records.append({
                "mukey": str(r[idx_mukey]),
                "musym": str(r[idx_musym]),
                "muname": str(r[idx_muname]),
                "geom_wkt": str(r[idx_wkt]),
            })
    return records


def lookup_soil_survey(
    parcel: Optional[dict] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    timeout: int = 12,
) -> Optional[dict]:
    """Fetch USDA Web Soil Survey data bounded by the property parcel AOI."""
    parcel_shape = None
    minx, miny, maxx, maxy = None, None, None, None

    if parcel and isinstance(parcel, dict) and parcel.get("geometry"):
        try:
            parcel_shape = shape(parcel["geometry"])
            if not parcel_shape.is_valid:
                parcel_shape = parcel_shape.buffer(0)
            if not parcel_shape.is_empty:
                minx, miny, maxx, maxy = parcel_shape.bounds
        except Exception:
            parcel_shape = None

    if (minx is None or miny is None) and lat is not None and lon is not None:
        delta = 0.0015
        minx, miny, maxx, maxy = lon - delta, lat - delta, lon + delta, lat + delta

    if minx is None or miny is None:
        return None

    aoi_wkt = build_aoi_wkt(minx, miny, maxx, maxy)

    try:
        raw_records = query_sda_soil_mapunits(aoi_wkt, timeout=timeout)
    except Exception as exc:
        # If network error or timeout occurs, return None so callers can fall back
        return None

    if not raw_records:
        return {
            "source": "USDA Web Soil Survey (Soil Data Access)",
            "aoi": {
                "bounds": [minx, miny, maxx, maxy],
                "wkt": aoi_wkt,
            },
            "summary": [],
            "geojson": {"type": "FeatureCollection", "features": []},
            "labelsGeojson": {"type": "FeatureCollection", "features": []},
        }

    by_symbol = {}
    for item in raw_records:
        wkt_str = item.get("geom_wkt", "")
        if not wkt_str or wkt_str == "None":
            continue
        try:
            g = wkt.loads(wkt_str)
            if not g.is_valid:
                g = g.buffer(0)
            if g.is_empty:
                continue
        except Exception:
            continue

        if parcel_shape is not None:
            clipped = g.intersection(parcel_shape)
            if clipped.is_empty:
                continue
        else:
            clipped = g

        musym = item["musym"]
        if musym not in by_symbol:
            by_symbol[musym] = {
                "mukey": item["mukey"],
                "musym": musym,
                "muname": item["muname"],
                "geoms": [],
            }
        by_symbol[musym]["geoms"].append(clipped)

    if not by_symbol:
        return {
            "source": "USDA Web Soil Survey (Soil Data Access)",
            "aoi": {
                "bounds": [minx, miny, maxx, maxy],
                "wkt": aoi_wkt,
            },
            "summary": [],
            "geojson": {"type": "FeatureCollection", "features": []},
            "labelsGeojson": {"type": "FeatureCollection", "features": []},
        }

    # Aggregate geometry by symbol
    aggregated = []
    total_area = parcel_shape.area if parcel_shape is not None else 0
    if total_area <= 0:
        total_area = sum(unary_union(info["geoms"]).area for info in by_symbol.values())

    for idx, (musym, info) in enumerate(by_symbol.items()):
        union_geom = unary_union(info["geoms"])
        if union_geom.is_empty:
            continue
        area_ratio = (union_geom.area / total_area) if total_area > 0 else 0
        raw_pct = area_ratio * 100.0
        color = SOIL_PALETTE[idx % len(SOIL_PALETTE)]
        aggregated.append({
            "mukey": info["mukey"],
            "musym": musym,
            "muname": info["muname"],
            "raw_pct": raw_pct,
            "geom": union_geom,
            "color": color,
        })

    # Sort descending by raw percentage
    aggregated.sort(key=lambda x: x["raw_pct"], reverse=True)

    # Normalize percentages to 1 decimal place and ensure sum is 100.0%
    rounded_pcts = [round(item["raw_pct"], 1) for item in aggregated]
    diff = round(100.0 - sum(rounded_pcts), 1)
    if aggregated and abs(diff) > 0 and abs(diff) < 2.0:
        # adjust the largest unit
        rounded_pcts[0] = round(rounded_pcts[0] + diff, 1)

    features = []
    labels = []
    summary = []

    for i, item in enumerate(aggregated):
        pct = rounded_pcts[i]
        musym = item["musym"]
        muname = item["muname"]
        color = item["color"]
        geom = item["geom"]

        summary.append({
            "mukey": item["mukey"],
            "musym": musym,
            "muname": muname,
            "percentage": pct,
            "color": color,
        })

        features.append({
            "type": "Feature",
            "id": f"soil-{musym}",
            "properties": {
                "mukey": item["mukey"],
                "musym": musym,
                "muname": muname,
                "percentage": pct,
                "color": color,
            },
            "geometry": mapping(geom),
        })

        # Generate centered label point for each polygon part
        parts = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
        for part in parts:
            if part.is_empty or part.area <= 0:
                continue
            rep_pt = part.representative_point()
            labels.append({
                "type": "Feature",
                "properties": {
                    "musym": musym,
                    "muname": muname,
                    "percentage": pct,
                    "color": color,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(rep_pt.x, 6), round(rep_pt.y, 6)],
                },
            })

    return {
        "source": "USDA Web Soil Survey (Soil Data Access)",
        "aoi": {
            "bounds": [minx, miny, maxx, maxy],
            "wkt": aoi_wkt,
        },
        "summary": summary,
        "geojson": {
            "type": "FeatureCollection",
            "features": features,
        },
        "labelsGeojson": {
            "type": "FeatureCollection",
            "features": labels,
        },
    }
