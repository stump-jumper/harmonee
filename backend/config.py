"""Application configuration, environment settings, and GIS service constants."""

import base64
import json
import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

DATA_FILE = BACKEND_DIR / "data.json"
CACHE_DIR = BACKEND_DIR / ".audubon_cache"
BIRD_PHOTO_CACHE_DIR = BACKEND_DIR / ".bird_cache"

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
EBIRD_API_KEY = os.getenv("EBIRD_API_KEY", "")
INATURALIST_USERNAME = os.getenv("INATURALIST_USERNAME", "")
INATURALIST_API_TOKEN = os.getenv("INATURALIST_API_TOKEN", "")
INATURALIST_API_BASE = "https://api.inaturalist.org/v1"


def get_mapbox_token() -> str:
    """Return active Mapbox token from environment or loaded config."""
    return os.getenv("MAPBOX_TOKEN") or MAPBOX_TOKEN


def get_ebird_api_key() -> str:
    """Return active eBird API key from environment or loaded config."""
    return os.getenv("EBIRD_API_KEY") or EBIRD_API_KEY


def get_inaturalist_api_token() -> str:
    """Return active iNaturalist JWT API token from environment or loaded config."""
    return os.getenv("INATURALIST_API_TOKEN") or INATURALIST_API_TOKEN


def get_inaturalist_username() -> str:
    """Return active iNaturalist username from environment, loaded config, or JWT."""
    username = os.getenv("INATURALIST_USERNAME") or INATURALIST_USERNAME
    if username:
        return username
    # If username is empty but token is present, we can decode user_id
    return ""


def get_inaturalist_user_id() -> str | int | None:
    """Extract numeric user_id from configured iNaturalist JWT token if available."""
    token = get_inaturalist_api_token()
    if not token or "." not in token:
        return None
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            payload_part = parts[1]
            payload_part += "=" * (-len(payload_part) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_part).decode("utf-8"))
            return payload.get("user_id")
    except Exception:
        return None
    return None


PARCEL_ENDPOINTS = [
    "https://mapservices.pasda.psu.edu/server/rest/services/pasda/LehighCounty/MapServer/5/query",
    "https://mapservices.pasda.psu.edu/server/rest/services/pasda/MontgomeryCounty/MapServer/14/query",
]

SUPPORTED_COUNTIES = [
    {
        "name": "Lehigh County",
        "county": "Lehigh",
        "state": "PA",
        "displayName": "Lehigh County, PA",
    },
    {
        "name": "Montgomery County",
        "county": "Montgomery",
        "state": "PA",
        "displayName": "Montgomery County, PA",
    },
]

SUPPORTED_COUNTY_NAMES = {"lehigh", "lehigh county", "montgomery", "montgomery county"}
SUPPORTED_STATES = {"pennsylvania", "pa", "us-pa"}

# Geographic bounds enclosing Lehigh and Montgomery Counties, PA
SUPPORTED_COUNTIES_BBOX = "-75.95,39.95,-75.00,40.82"
SUPPORTED_COUNTIES_CENTER = "-75.40,40.35"

ECOREGION_ENDPOINTS = [
    "https://services.arcgis.com/neT9SoYxizqTHZPH/arcgis/rest/services/EPA_Region_3_Ecoregion_Level_IV/FeatureServer/0/query",
    "https://services2.arcgis.com/FiaPA4ga0iQKduv3/arcgis/rest/services/Level_III_Ecoregions_in_the_US_v1/FeatureServer/0/query",
]
