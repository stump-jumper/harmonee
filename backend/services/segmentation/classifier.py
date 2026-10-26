"""User-guided interactive satellite habitat feature extraction and parcel segmentation."""

import io
import logging
from typing import Optional
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from backend.services.segmentation.geometry import (
    clean_polygonal,
    merge_small_regions,
    raster_mask_to_spline_polygon,
)

logger = logging.getLogger("harmonee.segmentation")

HABITAT_CLASSES = [
    {
        "id": "tree_canopy",
        "name": "Tree Canopy",
        "color": "#15803d",
        "description": "Deciduous and evergreen woody tree canopy and mature woodland",
    },
    {
        "id": "low_vegetation",
        "name": "Low Vegetation",
        "color": "#4ade80",
        "description": "Herbaceous cover including managed lawn, open grass, and meadow",
    },
    {
        "id": "impervious_surfaces",
        "name": "Impervious Surfaces",
        "color": "#94a3af",
        "description": "Roofs, buildings, paved roads, driveways, sidewalks, and parking surfaces",
    },
    {
        "id": "water",
        "name": "Water",
        "color": "#38bdf8",
        "description": "Open water including ponds, streams, rivers, and swimming pools",
    },
    {
        "id": "barren",
        "name": "Barren",
        "color": "#d97706",
        "description": "Bare soil, sand, mulch, landscaping beds, and exposed earth",
    },
]

HABITAT_LOOKUP = {c["id"]: c for c in HABITAT_CLASSES}


def fetch_satellite_patch(
    minx: float, miny: float, maxx: float, maxy: float, mapbox_token: str, size: int = 384
) -> Optional[Image.Image]:
    """Fetch static satellite imagery covering the exact bounding box [minx, miny, maxx, maxy]."""
    if not mapbox_token:
        return None
    bbox_str = f"[{minx:.6f},{miny:.6f},{maxx:.6f},{maxy:.6f}]"
    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{bbox_str}/{size}x{size}@2x?access_token={mapbox_token}&attribution=false&logo=false"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "HarmoneeApp/1.0"})
        with urllib.request.urlopen(req, timeout=8.0) as resp:
            return Image.open(io.BytesIO(resp.read())).convert("RGB")
    except Exception as e:
        logger.warning(f"Failed to fetch satellite patch: {e}")
        return None


def _extract_image_features(img: Image.Image) -> np.ndarray:
    """Extract 7-channel pixel feature stack [R, G, B, Lum, ExG, Sat, Texture * 3.5]."""
    rgb_arr = np.asarray(img, dtype=np.float32) / 255.0
    r = rgb_arr[:, :, 0]
    g = rgb_arr[:, :, 1]
    b = rgb_arr[:, :, 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    exg = 2.0 * g - r - b
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)
    sat = (max_c - min_c) / (max_c + 1e-5)

    gray_img = img.convert("L")
    gray_arr = np.asarray(gray_img, dtype=np.float32) / 255.0
    gray_blur = (
        np.asarray(gray_img.filter(ImageFilter.GaussianBlur(radius=2.0)), dtype=np.float32)
        / 255.0
    )
    texture = np.abs(gray_arr - gray_blur)
    return np.stack([r, g, b, lum, exg, sat, texture * 3.5], axis=-1)


def segment_parcel_from_user_paint(
    parcel_feature: dict, strokes: list[dict], mapbox_token: str = ""
) -> dict:
    """Segment satellite imagery strictly within parcel_feature based on user-painted seed strokes."""
    if not parcel_feature or not parcel_feature.get("geometry"):
        return {"layers": [], "classificationSystem": "User-Guided Interactive Segmentation"}

    parcel_geom = clean_polygonal(shape(parcel_feature["geometry"]))
    if parcel_geom.is_empty:
        return {"layers": [], "classificationSystem": "User-Guided Interactive Segmentation"}

    valid_strokes = []
    for s in strokes or []:
        if not isinstance(s, dict) or not s.get("coordinates") or len(s.get("coordinates")) == 0:
            continue
        cat_id = s.get("categoryId")
        if cat_id in ("impervious_structures", "impervious_surfaces"):
            cat_id = "impervious_surfaces"
        if cat_id in HABITAT_LOOKUP:
            s_copy = dict(s)
            s_copy["categoryId"] = cat_id
            valid_strokes.append(s_copy)

    minx, miny, maxx, maxy = parcel_geom.bounds
    pad_x = (maxx - minx) * 0.05
    pad_y = (maxy - miny) * 0.05
    q_minx, q_maxx = minx - pad_x, maxx + pad_x
    q_miny, q_maxy = miny - pad_y, maxy + pad_y

    w_px, h_px = 384, 384
    img = fetch_satellite_patch(q_minx, q_miny, q_maxx, q_maxy, mapbox_token, size=384)
    if img is None:
        img = Image.new("RGB", (w_px, h_px), (45, 95, 65))
    else:
        img = img.resize((w_px, h_px), Image.Resampling.BILINEAR)

    p_mask_img = Image.new("L", (w_px, h_px), 0)
    draw = ImageDraw.Draw(p_mask_img)

    def to_px(lon_val: float, lat_val: float) -> tuple[float, float]:
        px = (lon_val - q_minx) / (q_maxx - q_minx) * w_px
        py = (q_maxy - lat_val) / (q_maxy - q_miny) * h_px
        return (px, py)

    parcel_polys = [parcel_geom] if isinstance(parcel_geom, Polygon) else list(parcel_geom.geoms)
    for poly in parcel_polys:
        ext_pts = [to_px(x, y) for x, y in poly.exterior.coords]
        if len(ext_pts) >= 3:
            draw.polygon(ext_pts, fill=255)
        for interior in poly.interiors:
            hole_pts = [to_px(x, y) for x, y in interior.coords]
            if len(hole_pts) >= 3:
                draw.polygon(hole_pts, fill=0)

    valid_mask = np.asarray(p_mask_img) > 127
    dilated_mask = np.asarray(p_mask_img.filter(ImageFilter.MaxFilter(9))) > 127

    if not valid_strokes:
        return {
            "layers": [],
            "needsUserPaint": True,
            "message": "Click 'Paint Habitat Seeds' to draw over your trees, lawn, driveway, and structures, then run segmentation.",
            "classificationSystem": "User-Guided Interactive Segmentation",
        }

    feature_stack = _extract_image_features(img)

    stroke_masks: dict[str, Image.Image] = {}
    categories_present: list[str] = []

    for s in valid_strokes:
        cat_id = s["categoryId"]
        if cat_id not in stroke_masks:
            stroke_masks[cat_id] = Image.new("L", (w_px, h_px), 0)
            categories_present.append(cat_id)
        s_draw = ImageDraw.Draw(stroke_masks[cat_id])
        coords = s["coordinates"]
        pts = [to_px(pt[0], pt[1]) for pt in coords]
        rad_m = float(s.get("radiusMeters") or 4.0)
        r_px = max(2, int(round((rad_m / 111320.0) / (q_maxy - q_miny) * h_px)))

        if len(pts) >= 2:
            s_draw.line(pts, fill=255, width=r_px * 2)
        for px, py in pts:
            s_draw.ellipse([px - r_px, py - r_px, px + r_px, py + r_px], fill=255)

    scores: list[np.ndarray] = []
    for cat_id in categories_present:
        mask_arr = np.asarray(stroke_masks[cat_id]) > 127
        seed_pixels = mask_arr & dilated_mask
        if not np.any(seed_pixels):
            seed_pixels = mask_arr
        if not np.any(seed_pixels):
            scores.append(np.full((h_px, w_px), -1e9, dtype=np.float32))
            continue

        feats = feature_stack[seed_pixels]
        mu = np.mean(feats, axis=0)
        std = np.std(feats, axis=0) + 1.2e-2

        norm_diff = (feature_stack - mu) / std
        d_feat = np.sum(norm_diff ** 2, axis=-1)

        spatial_blur = (
            np.asarray(
                stroke_masks[cat_id].filter(ImageFilter.GaussianBlur(radius=22.0)),
                dtype=np.float32,
            )
            / 255.0
        )
        spatial_prior = np.log(spatial_blur + 0.005)

        score = -d_feat + 2.4 * spatial_prior
        score[mask_arr] += 50.0
        scores.append(score)

    if not scores:
        return {"layers": [], "classificationSystem": "User-Guided Interactive Segmentation"}

    score_stack = np.stack(scores, axis=0)
    labels = np.argmax(score_stack, axis=0)

    labels = merge_small_regions(labels, dilated_mask, min_pixels=25)
    labels = merge_small_regions(labels, dilated_mask, min_pixels=25)

    dx = (q_maxx - q_minx) / float(w_px)
    dy = (q_maxy - q_miny) / float(h_px)
    pixel_scale = max(dx, dy)
    simplify_tol = pixel_scale * 1.15
    min_hole_area = (pixel_scale * 5.0) ** 2

    remaining_parcel = parcel_geom
    cumulative_mask = np.zeros_like(valid_mask, dtype=bool)
    assigned_geoms: dict[str, Polygon | MultiPolygon] = {}
    min_sliver_area = 25.0 / (111320.0 ** 2 * 0.76)

    for pos, cat_id in enumerate(categories_present):
        if remaining_parcel.is_empty:
            break
        if pos == len(categories_present) - 1:
            assigned_geoms[cat_id] = clean_polygonal(remaining_parcel, min_area=min_sliver_area)
            remaining_parcel = Polygon()
        else:
            cls_mask = (labels == pos) & dilated_mask
            combined_mask = cls_mask | cumulative_mask
            smooth_poly = raster_mask_to_spline_polygon(
                combined_mask,
                q_minx,
                q_miny,
                q_maxx,
                q_maxy,
                simplify_tol=simplify_tol,
                min_hole_area=min_hole_area,
            )
            clipped = clean_polygonal(
                remaining_parcel.intersection(smooth_poly), min_area=min_sliver_area
            )
            if not clipped.is_empty:
                diff = clean_polygonal(
                    remaining_parcel.difference(clipped), min_area=min_sliver_area
                )
                assigned_geoms[cat_id] = clean_polygonal(
                    remaining_parcel.difference(diff), min_area=min_sliver_area
                )
                remaining_parcel = diff
                cumulative_mask = combined_mask

    if not remaining_parcel.is_empty and categories_present:
        last_cat = categories_present[-1]
        prev = assigned_geoms.get(last_cat, Polygon())
        assigned_geoms[last_cat] = clean_polygonal(
            unary_union([prev, remaining_parcel]), min_area=min_sliver_area
        )

    total_parcel_area = max(1e-12, parcel_geom.area)
    result_layers = []

    for cat in HABITAT_CLASSES:
        cat_id = cat["id"]
        geom = assigned_geoms.get(cat_id)
        if geom is None or geom.is_empty:
            continue
        geom = orient(geom, sign=1.0)
        pct = round((geom.area / total_parcel_area) * 100.0, 1)
        if pct <= 0.0:
            continue
        result_layers.append(
            {
                "id": f"habitat-{cat_id}",
                "categoryId": cat_id,
                "name": cat["name"],
                "color": cat["color"],
                "description": cat["description"],
                "percentage": pct,
                "feature": {
                    "type": "Feature",
                    "properties": {
                        "categoryId": cat_id,
                        "name": cat["name"],
                        "color": cat["color"],
                        "percentage": pct,
                    },
                    "geometry": mapping(geom),
                },
            }
        )

    return {
        "layers": result_layers,
        "classificationSystem": "User-Guided Interactive Habitat Segmentation",
    }


def segment_parcel_habitats(parcel_feature: dict, mapbox_token: str = "") -> dict:
    """Convenience wrapper for address updates when no custom paint strokes are passed."""
    return segment_parcel_from_user_paint(parcel_feature, [], mapbox_token)
