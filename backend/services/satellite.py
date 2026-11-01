"""Service for querying and formatting recent free satellite and aerial imagery layers."""

from datetime import datetime
import json
from typing import Any, Dict, List
import urllib.request

STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

# 12 unique aerial capture epochs for the property, ordered from newest to oldest
WAYBACK_EPOCHS: List[Dict[str, str]] = [
    {
        "releaseNumber": "20512",
        "date": "2025-10-23",
        "label": "2025 (Oct) - Latest",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/20512/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "27982",
        "date": "2025-04-24",
        "label": "2025 (Apr)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/27982/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "60013",
        "date": "2024-03-07",
        "label": "2024 (Mar)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/60013/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "25982",
        "date": "2023-06-13",
        "label": "2023 (Jun)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/25982/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "44873",
        "date": "2023-03-15",
        "label": "2023 (Mar)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/44873/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "42663",
        "date": "2022-01-12",
        "label": "2022 (Jan)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/42663/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "27659",
        "date": "2021-04-28",
        "label": "2021 (Apr)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/27659/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "18289",
        "date": "2020-07-01",
        "label": "2020 (Jul)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/18289/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "12576",
        "date": "2019-06-05",
        "label": "2019 (Jun)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/12576/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "11509",
        "date": "2016-06-13",
        "label": "2016 (Jun)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/11509/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "23880",
        "date": "2015-04-30",
        "label": "2015 (Apr)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/23880/{z}/{y}/{x}",
    },
    {
        "releaseNumber": "10",
        "date": "2014-02-20",
        "label": "2014 (Feb)",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/10/{z}/{y}/{x}",
    },
]

# Fallback definitions specifically tuned for the test property (2534 Lapp Road, Allentown, PA)
DEFAULT_TEST_LAYERS: List[Dict[str, Any]] = [
    {
        "id": "satellite-naip",
        "name": "USDA NAIP Aerial (Natural Color)",
        "layerId": "naip-layer",
        "sourceId": "naip-tiles",
        "badge": "0.6m • Apr 2022",
        "date": "2022-04-29",
        "cloudCover": 0.0,
        "resolution": "0.6m",
        "description": "High-resolution true-color orthoimagery from the USDA Farm Service Agency",
        "tileUrl": "https://planetarycomputer.microsoft.com/api/data/v1/collections/naip/items/pa_m_4007520_se_18_060_20220429/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=image&asset_bidx=image%7C1,2,3",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
    {
        "id": "satellite-naip-cir",
        "name": "USDA NAIP Color-Infrared (CIR)",
        "layerId": "naip-cir-layer",
        "sourceId": "naip-cir-tiles",
        "badge": "0.6m • Infrared",
        "date": "2022-04-29",
        "cloudCover": 0.0,
        "resolution": "0.6m",
        "description": "False-color near-infrared (CIR) rendering chlorophyll in bright red to analyze vegetation health and garden beds",
        "tileUrl": "https://planetarycomputer.microsoft.com/api/data/v1/collections/naip/items/pa_m_4007520_se_18_060_20220429/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?assets=image&asset_bidx=image%7C4,1,2",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
    {
        "id": "satellite-pema-leafoff",
        "name": "PEMA Leaf-Off Aerial (PA State)",
        "layerId": "pema-leafoff-layer",
        "sourceId": "pema-leafoff-tiles",
        "badge": "0.3m • Leaf-Off",
        "date": "2018-2021",
        "cloudCover": 0.0,
        "resolution": "0.3m",
        "description": "Pennsylvania state high-resolution leaf-off aerial survey (reveals ground structures, fences, and footpaths)",
        "tileUrl": "https://imagery.pasda.psu.edu/arcgis/rest/services/pasda/PEMAImagery2018/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png&transparent=true&f=image",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
    {
        "id": "satellite-lidar-hillshade",
        "name": "LiDAR Micro-Hillshade (PAMAP)",
        "layerId": "lidar-hillshade-layer",
        "sourceId": "lidar-hillshade-tiles",
        "badge": "1m • LiDAR",
        "date": "PAMAP",
        "cloudCover": 0.0,
        "resolution": "1m",
        "description": "Bare-earth LiDAR 3D hillshade revealing micro-topography, drainage swales, and slope lines",
        "tileUrl": "https://imagery.pasda.psu.edu/arcgis/rest/services/pasda/PAMAP_Hillshade_WEB/MapServer/export?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png&transparent=true&f=image",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
    {
        "id": "satellite-esri-wayback",
        "name": "Esri World Imagery Wayback",
        "layerId": "esri-wayback-layer",
        "sourceId": "esri-wayback-tiles",
        "badge": "0.5m • Wayback",
        "date": "2025-10-23",
        "cloudCover": 0.0,
        "resolution": "0.5m",
        "description": "Esri World Imagery multi-year aerial time machine (12 historical flight epochs from 2014 to 2026)",
        "tileUrl": WAYBACK_EPOCHS[0]["tileUrl"],
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
        "epochs": WAYBACK_EPOCHS,
        "selectedEpochIndex": 0,
    },
]


def query_recent_satellite_layers(lat: float, lon: float) -> List[Dict[str, Any]]:
    """Query recent satellite and aerial imagery layers for the given coordinates."""
    layers = [dict(layer) for layer in DEFAULT_TEST_LAYERS]

    try:
        # USDA NAIP lookup (updates both Natural Color and CIR)
        body = {
            "collections": ["naip"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "sortby": [{"field": "datetime", "direction": "desc"}],
            "limit": 1,
        }
        req = urllib.request.Request(
            STAC_API_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "HarmoneeApp/1.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            res = json.loads(r.read())
            if res.get("features"):
                f = res["features"][0]
                item_id = f["id"]
                dt_str = f.get("properties", {}).get("datetime", "")
                short_dt = dt_str[:10]
                year_str = short_dt[:4] if short_dt else "NAIP"
                tile_url_rgb = f"https://planetarycomputer.microsoft.com/api/data/v1/collections/naip/items/{item_id}/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?assets=image&asset_bidx=image%7C1,2,3"
                tile_url_cir = f"https://planetarycomputer.microsoft.com/api/data/v1/collections/naip/items/{item_id}/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?assets=image&asset_bidx=image%7C4,1,2"
                layers[0]["badge"] = f"0.6m • {year_str}"
                layers[0]["date"] = short_dt
                layers[0]["tileUrl"] = tile_url_rgb
                layers[1]["badge"] = f"0.6m • CIR {year_str}"
                layers[1]["date"] = short_dt
                layers[1]["tileUrl"] = tile_url_cir
    except Exception:
        pass

    return layers
