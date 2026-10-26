"""EPA Ecoregion classification and Keystone Native Plant ranking services."""

import json
import re
import urllib.parse
import urllib.request
from typing import Optional

from backend import config
from backend.data.ecoregion_data import LEVEL_IV_DESCRIPTIONS
from backend.data.keystone_plants import KEYSTONE_PLANT_DATASET


def format_ecoregion_name(name: Optional[str]) -> str:
    """Normalize uppercase EPA ecoregion names into title case."""
    if not name:
        return ""
    text = str(name).strip()
    if text.isupper():
        text = text.title().replace("Usa", "USA")
    return text


def describe_level4(l4_code: str, l4_name: str, l3_name: str, l1_name: str) -> str:
    """Return narrative description for an EPA Level IV ecoregion code or synthesized fallback."""
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
    for endpoint in config.ECOREGION_ENDPOINTS:
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


def lookup_keystone_plants(lat: float, lon: float, ecoregions: Optional[dict] = None) -> dict:
    """Rank top 3 native trees/shrubs and top 3 native flowers/grasses by Lepidoptera host count."""
    l1_str = (ecoregions or {}).get("level1") or ""
    l1_match = re.match(r"^\s*(\d+)", l1_str)
    l1_code = l1_match.group(1) if l1_match else "8"

    profile = KEYSTONE_PLANT_DATASET.get(l1_code) or KEYSTONE_PLANT_DATASET["8"]

    # Query local botanical observations within 20 km to identify locally verified species per genus
    local_species_by_genus: dict[str, list[str]] = {}
    try:
        inat_params = urllib.parse.urlencode(
            {
                "lat": round(lat, 4),
                "lng": round(lon, 4),
                "radius": 20,
                "taxon_id": 47126,  # Plantae
                "quality_grade": "research",
                "native": "true",
                "per_page": 60,
            }
        )
        req = urllib.request.Request(
            f"https://api.inaturalist.org/v1/observations/species_counts?{inat_params}",
            headers={"User-Agent": "HarmoneeApp/1.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            for item in payload.get("results", []):
                taxon = item.get("taxon") or {}
                sci = taxon.get("name") or ""
                com = taxon.get("preferred_common_name") or ""
                parts = sci.split()
                if len(parts) >= 2 and com:
                    genus = parts[0]
                    formatted = f"{com.title()} ({parts[0][0]}. {parts[1]})"
                    bucket = local_species_by_genus.setdefault(genus, [])
                    if formatted not in bucket and len(bucket) < 2:
                        bucket.append(formatted)
    except Exception:
        pass

    def build_top_list(items: list[dict], limit: int = 3) -> list[dict]:
        enriched = []
        for entry in items:
            genus = entry["genus"]
            local_examples = local_species_by_genus.get(genus)
            enriched.append(
                {
                    "commonName": entry["commonName"],
                    "genus": f"{genus} spp.",
                    "exampleSpecies": (
                        ", ".join(local_examples) if local_examples else entry["exampleSpecies"]
                    ),
                    "lepidopteraCount": entry["lepidopteraCount"],
                    "locallyVerified": bool(local_examples),
                }
            )
        enriched.sort(key=lambda x: x["lepidopteraCount"], reverse=True)
        return enriched[:limit]

    return {
        "treesAndShrubs": build_top_list(profile["treesAndShrubs"], 3),
        "flowersAndGrasses": build_top_list(profile["flowersAndGrasses"], 3),
        "methodology": "Tallamy & Shropshire (UD/USFS) Lepidoptera Host-Plant Index + EPA Ecoregion Flora",
    }
