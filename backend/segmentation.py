"""User-driven interactive habitat autosegmentation strictly bounded by property parcels.

The user paints / scribbles seed areas on the satellite imagery for target habitat classes.
The algorithm extracts multi-scale color (RGB, Lum, ExG, Sat) and high-frequency texture features,
models the user-painted seed distributions, propagates classes via feature distance and spatial proximity,
merges minor specks, fits smooth Catmull-Rom splines, and strictly carves within the parcel boundary
with 0% overlap and 0% gaps.

Classes:
  - tree_canopy: Tree Canopy (#15803d)
  - low_vegetation: Low Vegetation / Lawn (#4ade80)
  - impervious_surfaces: Impervious Surfaces (#94a3af)
  - water: Water (#38bdf8)
  - barren: Barren / Exposed Earth (#d97706)
"""

import io
import logging
import urllib.request
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

logger = logging.getLogger("harmonee.segmentation")

# Standardized Habitat Categories
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


def _clean_polygonal(geom, min_area: float = 0.0):
    """
    Extract valid Polygon/MultiPolygon parts above min_area, dissolve razor-thin
    degenerate slivers via subtle morphological opening, and enforce RFC 7946
    right-hand rule ring orientation (CCW exterior, CW holes) to prevent triangulation glitches.
    """
    if geom is None or geom.is_empty:
        return Polygon()
    if not geom.is_valid:
        geom = geom.buffer(0)

    # Shave off sub-meter razor needles and corner slivers
    eps = 0.85 / 111320.0
    opened = geom.buffer(-eps).buffer(eps)
    if not opened.is_empty and opened.is_valid:
        geom = opened

    polys = (
        [geom]
        if isinstance(geom, Polygon)
        else list(geom.geoms)
        if hasattr(geom, "geoms")
        else []
    )
    kept = []
    for g in polys:
        if isinstance(g, (Polygon, MultiPolygon)) and not g.is_empty and g.area >= min_area:
            # Check compactness to filter out degenerate long knife-edge slivers
            compactness = (4.0 * np.pi * g.area) / (g.length ** 2) if g.length > 0 else 0
            if compactness > 0.002 or g.area > (min_area * 5.0):
                kept.append(g)

    if not kept:
        return Polygon()
    u = unary_union(kept)
    if not u.is_valid:
        u = u.buffer(0)
    return orient(u, sign=1.0)


def _merge_small_regions(labels: np.ndarray, valid_mask: np.ndarray, min_pixels: int) -> np.ndarray:
    """
    Absorb small connected components (< min_pixels) into their longest-border neighbor
    to produce broad, cohesive habitat segments without distracting single-pixel noise.
    """
    h, w = labels.shape
    out = labels.copy()
    visited = np.zeros((h, w), dtype=bool)

    for r in range(h):
        for c in range(w):
            if not valid_mask[r, c] or visited[r, c]:
                continue
            cls = out[r, c]
            queue = [(r, c)]
            visited[r, c] = True
            comp = [(r, c)]
            neighbor_counts: dict[int, int] = {}

            head = 0
            while head < len(queue):
                cr, cc = queue[head]
                head += 1
                for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
                    if 0 <= nr < h and 0 <= nc < w and valid_mask[nr, nc]:
                        ncls = int(out[nr, nc])
                        if ncls == cls:
                            if not visited[nr, nc]:
                                visited[nr, nc] = True
                                queue.append((nr, nc))
                                comp.append((nr, nc))
                        else:
                            neighbor_counts[ncls] = neighbor_counts.get(ncls, 0) + 1

            if len(comp) < min_pixels and neighbor_counts:
                best_neighbor = max(neighbor_counts.items(), key=lambda kv: kv[1])[0]
                for pr, pc in comp:
                    out[pr, pc] = best_neighbor

    return out


def _catmull_rom_spline_ring(coords, subdivisions: int = 4) -> list[tuple[float, float]]:
    """
    Interpolate a closed Centripetal Catmull-Rom spline through polygon ring coordinates.
    Unlike standard B-splines which pull inward and round off real corners, Catmull-Rom splines
    pass smoothly through each simplified control vertex, preserving true boundary detail.
    """
    pts = list(coords)
    if len(pts) < 4:
        return pts
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        return coords

    pts_arr = np.asarray(pts, dtype=np.float64)
    curve = []
    for i in range(n):
        p0 = pts_arr[(i - 1) % n]
        p1 = pts_arr[i]
        p2 = pts_arr[(i + 1) % n]
        p3 = pts_arr[(i + 2) % n]
        for t in np.linspace(0.0, 1.0, subdivisions, endpoint=False):
            t2 = t * t
            t3 = t2 * t
            q = 0.5 * (
                (2.0 * p1)
                + (-p0 + p2) * t
                + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
            )
            curve.append((float(q[0]), float(q[1])))
    if curve:
        curve.append(curve[0])
    return curve


def _smooth_polygon_spline(
    geom, simplify_tol: float, min_hole_area: float
) -> Polygon | MultiPolygon:
    """Convert boxy raster geometries into clean, continuous Catmull-Rom splines."""
    geom = _clean_polygonal(geom)
    if geom.is_empty:
        return Polygon()

    polys = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
    smoothed_polys = []

    for poly in polys:
        simp = poly.simplify(simplify_tol, preserve_topology=True)
        if simp.is_empty:
            simp = poly

        sub_polys = [simp] if isinstance(simp, Polygon) else list(simp.geoms)
        for sp in sub_polys:
            ext_spline = _catmull_rom_spline_ring(sp.exterior.coords, subdivisions=4)
            if len(ext_spline) < 4:
                continue
            holes = []
            for interior in sp.interiors:
                if Polygon(interior).area < min_hole_area:
                    continue
                h_spline = _catmull_rom_spline_ring(interior.coords, subdivisions=4)
                if len(h_spline) >= 4:
                    holes.append(h_spline)
            try:
                cand = Polygon(ext_spline, holes)
                if not cand.is_valid:
                    cand = cand.buffer(0)
                cand = _clean_polygonal(cand)
                if not cand.is_empty:
                    smoothed_polys.append(cand)
            except Exception:
                smoothed_polys.append(sp)

    if not smoothed_polys:
        return geom
    return _clean_polygonal(unary_union(smoothed_polys))


def _raster_mask_to_spline_polygon(
    mask: np.ndarray,
    minx: float,
    miny: float,
    maxx: float,
    maxy: float,
    simplify_tol: float,
    min_hole_area: float,
) -> Polygon | MultiPolygon:
    """Convert a 2D boolean mask to a smooth Catmull-Rom spline polygon geometry."""
    h, w = mask.shape
    if not np.any(mask):
        return Polygon()

    dx = (maxx - minx) / float(w)
    dy = (maxy - miny) / float(h)

    row_boxes = []
    for r in range(h):
        row = mask[r]
        if not np.any(row):
            continue
        padded = np.concatenate(([False], row, [False]))
        starts = np.where(padded[1:] & ~padded[:-1])[0]
        ends = np.where(~padded[1:] & padded[:-1])[0]
        y_top = maxy - r * dy
        y_bot = maxy - (r + 1) * dy
        for s, e in zip(starts, ends):
            x_left = minx + s * dx
            x_right = minx + e * dx
            row_boxes.append(
                Polygon(
                    [
                        (x_left, y_bot),
                        (x_right, y_bot),
                        (x_right, y_top),
                        (x_left, y_top),
                    ]
                )
            )

    if not row_boxes:
        return Polygon()

    raw_union = _clean_polygonal(unary_union(row_boxes))
    if raw_union.is_empty:
        return Polygon()

    return _smooth_polygon_spline(
        raw_union, simplify_tol=simplify_tol, min_hole_area=min_hole_area
    )


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


def segment_parcel_from_user_paint(
    parcel_feature: dict, strokes: list[dict], mapbox_token: str = ""
) -> dict:
    """
    Segment the satellite imagery strictly within `parcel_feature` based on user-painted seed strokes.
    Each stroke provides ground-truth class samples on the actual image.

    The algorithm:
    1. Rasterizes the parcel boundary.
    2. Extracts color (RGB, Lum, ExG, Sat) and texture features from the high-res satellite image.
    3. Samples the user's paint strokes to establish class feature models (mean & std).
    4. Computes feature similarity and spatial proximity heatmaps from strokes.
    5. Classifies all parcel pixels, merges small noise, fits smooth Catmull-Rom splines,
       and iteratively difference-carves against the parcel (0% overlap, 0% gaps).
    """
    if not parcel_feature or not parcel_feature.get("geometry"):
        return {"layers": [], "classificationSystem": "User-Guided Interactive Segmentation"}

    parcel_geom = _clean_polygonal(shape(parcel_feature["geometry"]))
    if parcel_geom.is_empty:
        return {"layers": [], "classificationSystem": "User-Guided Interactive Segmentation"}

    # Filter valid strokes that match known categories (normalizing legacy structure strokes)
    valid_strokes = []
    for s in (strokes or []):
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

    # 1. Parcel raster mask
    p_mask_img = Image.new("L", (w_px, h_px), 0)
    draw = ImageDraw.Draw(p_mask_img)

    def to_px(lon_val: float, lat_val: float) -> tuple[float, float]:
        px = (lon_val - q_minx) / (q_maxx - q_minx) * w_px
        py = (q_maxy - lat_val) / (q_maxy - q_miny) * h_px
        return (px, py)

    parcel_polys = (
        [parcel_geom] if isinstance(parcel_geom, Polygon) else list(parcel_geom.geoms)
    )
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

    # If no user strokes exist yet, create initial balanced seed hints based on image contrast
    if not valid_strokes:
        # Prompt user to paint
        return {
            "layers": [],
            "needsUserPaint": True,
            "message": "Click 'Paint Habitat Seeds' to draw over your trees, lawn, driveway, and structures, then run segmentation.",
            "classificationSystem": "User-Guided Interactive Segmentation",
        }

    # 2. Extract multi-scale color and texture features
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
    gray_blur = np.asarray(
        gray_img.filter(ImageFilter.GaussianBlur(radius=2.0)), dtype=np.float32
    ) / 255.0
    texture = np.abs(gray_arr - gray_blur)

    # Feature stack: [R, G, B, Lum, ExG, Sat, Texture * 3.5]
    feature_stack = np.stack([r, g, b, lum, exg, sat, texture * 3.5], axis=-1)

    # 3. Rasterize user strokes into seed masks per category
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
        # Approximate pixel radius from meters:
        r_px = max(2, int(round((rad_m / 111320.0) / (q_maxy - q_miny) * h_px)))

        if len(pts) >= 2:
            s_draw.line(pts, fill=255, width=r_px * 2)
        for px, py in pts:
            s_draw.ellipse([px - r_px, py - r_px, px + r_px, py + r_px], fill=255)

    # 4. Compute class likelihood and spatial proximity scores
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

        # Normalized feature distance
        norm_diff = (feature_stack - mu) / std
        d_feat = np.sum(norm_diff ** 2, axis=-1)

        # Spatial proximity influence from the user's stroke
        spatial_blur = (
            np.asarray(
                stroke_masks[cat_id].filter(ImageFilter.GaussianBlur(radius=22.0)),
                dtype=np.float32,
            )
            / 255.0
        )
        spatial_prior = np.log(spatial_blur + 0.005)

        # Combined energy score: feature similarity + spatial proximity
        score = -d_feat + 2.4 * spatial_prior
        # Hard stroke constraint: strongly prioritize the exact painted stroke pixels
        score[mask_arr] += 50.0
        scores.append(score)

    if not scores:
        return {"layers": [], "classificationSystem": "User-Guided Interactive Segmentation"}

    score_stack = np.stack(scores, axis=0)
    labels = np.argmax(score_stack, axis=0)

    # 5. Coarsen: absorb small isolated components (< 25 pixels ~ 25 m²) into neighbor habitat
    labels = _merge_small_regions(labels, dilated_mask, min_pixels=25)
    labels = _merge_small_regions(labels, dilated_mask, min_pixels=25)

    dx = (q_maxx - q_minx) / float(w_px)
    dy = (q_maxy - q_miny) / float(h_px)
    pixel_scale = max(dx, dy)
    simplify_tol = pixel_scale * 1.15
    min_hole_area = (pixel_scale * 5.0) ** 2

    # 6. Topological iterative carving against remaining_parcel (guarantees 0% overlap, 0% gaps)
    remaining_parcel = parcel_geom
    cumulative_mask = np.zeros_like(valid_mask, dtype=bool)
    assigned_geoms: dict[str, Polygon | MultiPolygon] = {}
    min_sliver_area = 25.0 / (111320.0 ** 2 * 0.76)

    for pos, cat_id in enumerate(categories_present):
        if remaining_parcel.is_empty:
            break
        if pos == len(categories_present) - 1:
            assigned_geoms[cat_id] = _clean_polygonal(remaining_parcel, min_area=min_sliver_area)
            remaining_parcel = Polygon()
        else:
            cls_mask = (labels == pos) & dilated_mask
            combined_mask = cls_mask | cumulative_mask
            smooth_poly = _raster_mask_to_spline_polygon(
                combined_mask,
                q_minx,
                q_miny,
                q_maxx,
                q_maxy,
                simplify_tol=simplify_tol,
                min_hole_area=min_hole_area,
            )
            clipped = _clean_polygonal(remaining_parcel.intersection(smooth_poly), min_area=min_sliver_area)
            if not clipped.is_empty:
                diff = _clean_polygonal(remaining_parcel.difference(clipped), min_area=min_sliver_area)
                assigned_geoms[cat_id] = _clean_polygonal(remaining_parcel.difference(diff), min_area=min_sliver_area)
                remaining_parcel = diff
                cumulative_mask = combined_mask

    if not remaining_parcel.is_empty and categories_present:
        last_cat = categories_present[-1]
        prev = assigned_geoms.get(last_cat, Polygon())
        assigned_geoms[last_cat] = _clean_polygonal(unary_union([prev, remaining_parcel]), min_area=min_sliver_area)

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
    # When no strokes are passed, prompt user to paint
    return segment_parcel_from_user_paint(parcel_feature, [], mapbox_token)
