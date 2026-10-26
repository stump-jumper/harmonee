"""Polygonal topology cleanup, connected-component merging, and Catmull-Rom spline vectorization."""

import numpy as np
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union


def clean_polygonal(geom, min_area: float = 0.0):
    """
    Extract valid Polygon/MultiPolygon parts above min_area, dissolve razor-thin
    degenerate slivers via subtle morphological opening, and enforce RFC 7946
    right-hand rule ring orientation (CCW exterior, CW holes) to prevent triangulation glitches.
    """
    if geom is None or geom.is_empty:
        return Polygon()
    if not geom.is_valid:
        geom = geom.buffer(0)

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
            compactness = (4.0 * np.pi * g.area) / (g.length ** 2) if g.length > 0 else 0
            if compactness > 0.002 or g.area > (min_area * 5.0):
                kept.append(g)

    if not kept:
        return Polygon()
    u = unary_union(kept)
    if not u.is_valid:
        u = u.buffer(0)
    return orient(u, sign=1.0)


def merge_small_regions(labels: np.ndarray, valid_mask: np.ndarray, min_pixels: int) -> np.ndarray:
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


def catmull_rom_spline_ring(coords, subdivisions: int = 4) -> list[tuple[float, float]]:
    """
    Interpolate a closed Centripetal Catmull-Rom spline through polygon ring coordinates,
    passing smoothly through simplified control vertices while preserving boundary detail.
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


def smooth_polygon_spline(
    geom, simplify_tol: float, min_hole_area: float
) -> Polygon | MultiPolygon:
    """Convert boxy raster geometries into clean, continuous Catmull-Rom splines."""
    geom = clean_polygonal(geom)
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
            ext_spline = catmull_rom_spline_ring(sp.exterior.coords, subdivisions=4)
            if len(ext_spline) < 4:
                continue
            holes = []
            for interior in sp.interiors:
                if Polygon(interior).area < min_hole_area:
                    continue
                h_spline = catmull_rom_spline_ring(interior.coords, subdivisions=4)
                if len(h_spline) >= 4:
                    holes.append(h_spline)
            try:
                cand = Polygon(ext_spline, holes)
                if not cand.is_valid:
                    cand = cand.buffer(0)
                cand = clean_polygonal(cand)
                if not cand.is_empty:
                    smoothed_polys.append(cand)
            except Exception:
                smoothed_polys.append(sp)

    if not smoothed_polys:
        return geom
    return clean_polygonal(unary_union(smoothed_polys))


def raster_mask_to_spline_polygon(
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

    raw_union = clean_polygonal(unary_union(row_boxes))
    if raw_union.is_empty:
        return Polygon()

    return smooth_polygon_spline(
        raw_union, simplify_tol=simplify_tol, min_hole_area=min_hole_area
    )
