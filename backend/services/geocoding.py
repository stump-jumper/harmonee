"""Address autocomplete geocoding and county boundary filtering services."""

import json
import urllib.parse
import urllib.request
from typing import Optional

from backend import config


def format_photon_feature(feature: dict, county: str = "") -> Optional[dict]:
    """Format an OpenStreetMap Photon GeoJSON feature into a standardized suggestion dict."""
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [])

    housenumber = props.get("housenumber", "")
    street = props.get("street") or props.get("name") or ""
    city = (
        props.get("city")
        or props.get("town")
        or props.get("village")
        or props.get("locality")
        or ""
    )
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
    item = {"label": label, "lat": lat, "lon": lon}
    if county:
        item["county"] = county
    return item


def extract_mapbox_county(feat: dict) -> Optional[str]:
    """Check if a Mapbox feature belongs to a supported county in PA, returning canonical county name or None."""
    context = feat.get("context", [])
    district_text = next(
        (c.get("text", "") for c in context if str(c.get("id", "")).startswith("district")),
        None,
    )
    if not district_text and str(feat.get("id", "")).startswith("district"):
        district_text = feat.get("text", "")

    region_text = next(
        (c.get("text", "") for c in context if str(c.get("id", "")).startswith("region")),
        None,
    )
    if not region_text and str(feat.get("id", "")).startswith("region"):
        region_text = feat.get("text", "")

    short_code = next(
        (c.get("short_code", "") for c in context if str(c.get("id", "")).startswith("region")),
        None,
    )

    place_name = feat.get("place_name", "")
    dist_norm = (district_text or "").strip().lower()
    reg_norm = (region_text or "").strip().lower()
    code_norm = (short_code or "").strip().lower()

    is_pa = reg_norm in config.SUPPORTED_STATES or code_norm in config.SUPPORTED_STATES
    if not is_pa and (", Pennsylvania" in place_name or ", PA" in place_name):
        is_pa = True

    if not is_pa:
        return None

    if dist_norm in ("lehigh", "lehigh county"):
        return "Lehigh County"
    if dist_norm in ("montgomery", "montgomery county"):
        return "Montgomery County"

    lower_place = place_name.lower()
    if "lehigh county" in lower_place:
        return "Lehigh County"
    if "montgomery county" in lower_place:
        return "Montgomery County"

    return None


def extract_photon_county(feat: dict) -> Optional[str]:
    """Check if a Photon feature belongs to a supported county in PA, returning canonical county name or None."""
    props = feat.get("properties", {})
    county = (props.get("county") or "").strip().lower()
    state = (props.get("state") or "").strip().lower()
    country = (props.get("country") or "").strip().lower()

    if state and state not in config.SUPPORTED_STATES:
        return None
    if country and country not in ("united states", "usa", "us"):
        return None

    if county in ("lehigh", "lehigh county"):
        return "Lehigh County"
    if county in ("montgomery", "montgomery county"):
        return "Montgomery County"

    return None


def lookup_suggestions(query: str) -> list[dict]:
    """Look up up to 5 geocoded address suggestions restricted to supported counties."""
    suggestions = []
    seen = set()
    mapbox_token = config.get_mapbox_token()

    # 1. Try Mapbox Geocoding API if token is configured (filtered to supported counties)
    if mapbox_token:
        try:
            encoded_q = urllib.parse.quote(query)
            params = urllib.parse.urlencode(
                {
                    "access_token": mapbox_token,
                    "autocomplete": "true",
                    "types": "address,place,postcode,district",
                    "country": "us",
                    "bbox": config.SUPPORTED_COUNTIES_BBOX,
                    "proximity": config.SUPPORTED_COUNTIES_CENTER,
                    "limit": 10,
                }
            )
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_q}.json?{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "HarmoneeApp/0.1"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for feat in payload.get("features", []):
                    county = extract_mapbox_county(feat)
                    if not county:
                        continue
                    label = feat.get("place_name")
                    center = feat.get("center", [])
                    if label and label not in seen and len(center) >= 2:
                        seen.add(label)
                        suggestions.append(
                            {
                                "label": label,
                                "lon": center[0],
                                "lat": center[1],
                                "county": county,
                            }
                        )
        except Exception:
            pass

    # 2. Fallback to Photon (OpenStreetMap search-as-you-type geocoder, filtered to supported counties)
    if not suggestions:
        try:
            params = urllib.parse.urlencode(
                {
                    "q": query,
                    "limit": 10,
                    "lang": "en",
                    "bbox": config.SUPPORTED_COUNTIES_BBOX,
                }
            )
            req = urllib.request.Request(
                f"https://photon.komoot.io/api/?{params}",
                headers={"User-Agent": "HarmoneeApp/0.1 (local-dev)"},
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for feat in payload.get("features", []):
                    county = extract_photon_county(feat)
                    if not county:
                        continue
                    item = format_photon_feature(feat, county=county)
                    if item and item["label"] not in seen:
                        seen.add(item["label"])
                        suggestions.append(item)
        except Exception:
            pass

    return suggestions[:5]
