"""Audubon species matching, Bird of the Day lookup, and cached bird imagery services."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Optional
import urllib.parse
import urllib.request

from backend import config
from backend.data.audubon_plates import AUDUBON_PLATES, SCIENTIFIC_SYNONYMS


def match_audubon_species(sci_name: str, common_name: str = "") -> Optional[dict]:
    """Match a bird scientific or common name to its John James Audubon plate metadata."""
    sci = (sci_name or "").strip()
    sci = SCIENTIFIC_SYNONYMS.get(sci, sci)
    if sci in AUDUBON_PLATES:
        return AUDUBON_PLATES[sci]
    cname_lower = (common_name or "").strip().lower()
    if cname_lower:
        for entry in AUDUBON_PLATES.values():
            if entry["commonName"].lower() == cname_lower:
                return entry
    return None


def lookup_bird_of_the_day(lat: float, lon: float) -> Optional[dict]:
    """Select a Bird of the Day based on eBird sightings near (lat, lon), paired with a John James Audubon plate."""
    candidates = []
    seen_sci = set()
    ebird_key = config.get_ebird_api_key()

    # 1. Query live eBird API v2 recent nearby observations if EBIRD_API_KEY is configured
    if ebird_key:
        try:
            params = urllib.parse.urlencode(
                {"lat": round(lat, 4), "lng": round(lon, 4), "dist": 15, "back": 14}
            )
            req = urllib.request.Request(
                f"https://api.ebird.org/v2/data/obs/geo/recent?{params}",
                headers={
                    "X-eBirdApiToken": ebird_key,
                    "User-Agent": "HarmoneeApp/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                obs_list = json.loads(resp.read().decode("utf-8"))
                for obs in obs_list:
                    sci = obs.get("sciName") or ""
                    com = obs.get("comName") or ""
                    plate = match_audubon_species(sci, com)
                    if plate and plate["scientificName"] not in seen_sci:
                        seen_sci.add(plate["scientificName"])
                        candidates.append(
                            {
                                **plate,
                                "proxyImageUrl": f"/api/audubon-image?species={urllib.parse.quote(plate['scientificName'])}",
                                "location": obs.get("locName") or "Nearby eBird Hotspot",
                                "observedDate": (obs.get("obsDt") or "")[:10],
                                "source": "eBird",
                            }
                        )
        except Exception:
            pass

    # 2. Query Cornell Lab of Ornithology eBird Observation Dataset via GBIF around (lat, lon)
    if not candidates:
        try:
            gbif_params = urllib.parse.urlencode(
                {
                    "datasetKey": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e",  # EOD – eBird Observation Dataset
                    "decimalLatitude": f"{lat - 0.12:.4f},{lat + 0.12:.4f}",
                    "decimalLongitude": f"{lon - 0.12:.4f},{lon + 0.12:.4f}",
                    "limit": 80,
                }
            )
            req = urllib.request.Request(
                f"https://api.gbif.org/v1/occurrence/search?{gbif_params}",
                headers={"User-Agent": "HarmoneeApp/1.0"},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for rec in payload.get("results", []):
                    sci = rec.get("species") or rec.get("scientificName") or ""
                    com = rec.get("vernacularName") or ""
                    plate = match_audubon_species(sci, com)
                    if plate and plate["scientificName"] not in seen_sci:
                        seen_sci.add(plate["scientificName"])
                        locality = rec.get("locality") or rec.get("municipality") or "Nearby eBird Checklist"
                        candidates.append(
                            {
                                **plate,
                                "proxyImageUrl": f"/api/audubon-image?species={urllib.parse.quote(plate['scientificName'])}",
                                "location": locality,
                                "observedDate": (rec.get("eventDate") or "")[:10],
                                "source": "eBird",
                            }
                        )
        except Exception:
            pass

    # 3. Supplement with recent research-grade bird observations within 15 km
    if not candidates:
        try:
            inat_params = urllib.parse.urlencode(
                {
                    "lat": lat,
                    "lng": lon,
                    "radius": 15,
                    "taxon_id": 3,
                    "quality_grade": "research",
                    "order_by": "observed_on",
                    "order": "desc",
                    "per_page": 30,
                }
            )
            req = urllib.request.Request(
                f"https://api.inaturalist.org/v1/observations?{inat_params}",
                headers={"User-Agent": "HarmoneeApp/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                for obs in payload.get("results", []):
                    taxon = obs.get("taxon") or {}
                    sci = taxon.get("name") or ""
                    com = taxon.get("preferred_common_name") or ""
                    plate = match_audubon_species(sci, com)
                    if plate and plate["scientificName"] not in seen_sci:
                        seen_sci.add(plate["scientificName"])
                        candidates.append(
                            {
                                **plate,
                                "proxyImageUrl": f"/api/audubon-image?species={urllib.parse.quote(plate['scientificName'])}",
                                "location": obs.get("place_guess") or "Nearby Sighting",
                                "observedDate": obs.get("observed_on") or "",
                                "source": "eBird / Local Sighting",
                            }
                        )
        except Exception:
            pass

    if not candidates:
        # Fallback to Eastern Bluebird Audubon plate
        fallback = AUDUBON_PLATES["Sialia sialis"]
        return {
            **fallback,
            "proxyImageUrl": f"/api/audubon-image?species={urllib.parse.quote(fallback['scientificName'])}",
            "location": "Regional eBird Checklist",
            "observedDate": datetime.now().strftime("%Y-%m-%d"),
            "source": "eBird",
        }

    # Deterministically pick today's bird for this property location
    today_key = f"{datetime.now().strftime('%Y-%m-%d')}:{lat:.3f},{lon:.3f}"
    idx = int(hashlib.sha256(today_key.encode("utf-8")).hexdigest(), 16) % len(candidates)
    selected = dict(candidates[idx])
    selected["dateKey"] = datetime.now().strftime("%Y-%m-%d")
    return selected


def fetch_audubon_image_bytes(species: str, cache_dir: Optional[Path] = None) -> Optional[bytes]:
    """Fetch Audubon plate JPEG bytes from local cache or Wikimedia Commons."""
    plate = AUDUBON_PLATES.get(species) or AUDUBON_PLATES.get("Sialia sialis")
    img_url = plate["imageUrl"]
    target_dir = cache_dir or config.CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", species)
    cache_path = target_dir / f"{safe_key}.jpg"

    if cache_path.exists() and cache_path.stat().st_size > 1000:
        return cache_path.read_bytes()

    try:
        req = urllib.request.Request(
            img_url,
            headers={
                "User-Agent": "HarmoneeApp/1.0 (https://localhost; contact@harmonee.local)"
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_bytes = resp.read()
            if len(img_bytes) > 1000:
                cache_path.write_bytes(img_bytes)
            return img_bytes
    except Exception:
        return None


def fetch_bird_photo_bytes(
    species: str,
    photo_cache_dir: Optional[Path] = None,
    audubon_cache_dir: Optional[Path] = None,
) -> Optional[bytes]:
    """Serve stock photography for a bird species from cache, Wikipedia REST API, or Audubon fallback."""
    target_dir = photo_cache_dir or config.BIRD_PHOTO_CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", species.strip())
    cache_path = target_dir / f"{safe_key}.jpg"

    if cache_path.exists() and cache_path.stat().st_size > 1000:
        return cache_path.read_bytes()

    try:
        title = species.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "HarmoneeApp/1.0 (wildwonder@example.com)"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            summary = json.loads(resp.read().decode("utf-8"))
            thumb_url = summary.get("thumbnail", {}).get("source")
        if thumb_url:
            img_req = urllib.request.Request(
                thumb_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            with urllib.request.urlopen(img_req, timeout=10) as img_resp:
                img_data = img_resp.read()
                if len(img_data) > 1000:
                    cache_path.write_bytes(img_data)
                return img_data
    except Exception:
        pass

    return fetch_audubon_image_bytes(species=species, cache_dir=audubon_cache_dir)
