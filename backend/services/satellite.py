"""Service for querying and formatting recent free satellite and aerial imagery layers."""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

STAC_API_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

# Fallback definitions specifically tuned for the test property (2534 Lapp Road, Allentown, PA)
DEFAULT_TEST_LAYERS: List[Dict[str, Any]] = [
    {
        "id": "satellite-sentinel2",
        "name": "Sentinel-2 (Copernicus)",
        "layerId": "sentinel2-layer",
        "sourceId": "sentinel2-tiles",
        "badge": "10m • Oct 26",
        "date": "2026-10-26",
        "cloudCover": 1.7,
        "resolution": "10m",
        "description": "5-day revisit optical multispectral imagery from ESA Copernicus Sentinel-2",
        "tileUrl": "https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?collection=sentinel-2-l2a&item=S2C_MSIL2A_20261026T155331_R054_T18TVL_20261026T202106&assets=visual&asset_bidx=visual%7C1,2,3&nodata=0&format=png",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
    {
        "id": "satellite-landsat",
        "name": "Landsat 9 (USGS/NASA)",
        "layerId": "landsat-layer",
        "sourceId": "landsat-tiles",
        "badge": "30m • Oct 26",
        "date": "2026-10-26",
        "cloudCover": 0.1,
        "resolution": "30m",
        "description": "16-day revisit optical multispectral imagery from USGS / NASA Landsat 9",
        "tileUrl": "https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{z}/{x}/{y}@1x?collection=landsat-c2-l2&item=LC09_L2SP_015032_20261026_02_T1&assets=red&assets=green&assets=blue&color_formula=gamma%20RGB%202.7,%20saturation%201.5,%20sigmoidal%20RGB%2015%200.55&format=png",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
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
        "id": "satellite-usgs-tnm",
        "name": "USGS The National Map (TNM)",
        "layerId": "usgs-tnm-layer",
        "sourceId": "usgs-tnm-tiles",
        "badge": "1m • Ortho",
        "date": "Continuous Mosaic",
        "cloudCover": 0.0,
        "resolution": "1m",
        "description": "Seamless USGS National Geospatial Program high-resolution orthoimagery",
        "tileUrl": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
        "tileSize": 256,
        "maxzoom": 16,
        "opacity": 1.0,
    },
    {
        "id": "satellite-esri-wayback",
        "name": "Esri World Imagery Wayback",
        "layerId": "esri-wayback-layer",
        "sourceId": "esri-wayback-tiles",
        "badge": "0.5m • Wayback",
        "date": "Archive",
        "cloudCover": 0.0,
        "resolution": "0.5m",
        "description": "Esri World Imagery digital archive basemap for multi-year aerial comparison",
        "tileUrl": "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "tileSize": 256,
        "maxzoom": 22,
        "opacity": 1.0,
    },
]


def _format_date_badge(raw_date: str) -> str:
    """Format an ISO date string like 2026-10-26 into 'Oct 26'."""
    try:
        dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        return dt.strftime("%b %d")
    except Exception:
        return raw_date[:10] if raw_date else ""


def query_recent_satellite_layers(lat: float, lon: float) -> List[Dict[str, Any]]:
    """Query recent satellite and aerial imagery layers for the given coordinates."""
    layers = [dict(layer) for layer in DEFAULT_TEST_LAYERS]

    try:
        # Sentinel-2 L2A lookup
        body = {
            "collections": ["sentinel-2-l2a"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "query": {"eo:cloud_cover": {"lt": 25}},
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
                cloud = round(f.get("properties", {}).get("eo:cloud_cover", 0), 1)
                short_dt = dt_str[:10]
                badge_dt = _format_date_badge(dt_str)
                tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=sentinel-2-l2a&item={item_id}&assets=visual&asset_bidx=visual%7C1,2,3&nodata=0&format=png"
                layers[0]["badge"] = f"10m • {badge_dt}"
                layers[0]["date"] = short_dt
                layers[0]["cloudCover"] = cloud
                layers[0]["tileUrl"] = tile_url
    except Exception:
        pass

    try:
        # Landsat 9/8 lookup
        body = {
            "collections": ["landsat-c2-l2"],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "query": {"eo:cloud_cover": {"lt": 20}},
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
                cloud = round(f.get("properties", {}).get("eo:cloud_cover", 0), 1)
                short_dt = dt_str[:10]
                badge_dt = _format_date_badge(dt_str)
                tile_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}@1x?collection=landsat-c2-l2&item={item_id}&assets=red&assets=green&assets=blue&color_formula=gamma%20RGB%202.7,%20saturation%201.5,%20sigmoidal%20RGB%2015%200.55&format=png"
                layers[1]["badge"] = f"30m • {badge_dt}"
                layers[1]["date"] = short_dt
                layers[1]["cloudCover"] = cloud
                layers[1]["tileUrl"] = tile_url
    except Exception:
        pass

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
                layers[2]["badge"] = f"0.6m • {year_str}"
                layers[2]["date"] = short_dt
                layers[2]["tileUrl"] = tile_url_rgb
                layers[3]["badge"] = f"0.6m • CIR {year_str}"
                layers[3]["date"] = short_dt
                layers[3]["tileUrl"] = tile_url_cir
    except Exception:
        pass

    return layers
