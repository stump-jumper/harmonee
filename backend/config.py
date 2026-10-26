"""Application configuration, environment settings, and GIS service constants."""

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


def get_mapbox_token() -> str:
    """Return active Mapbox token from environment or loaded config."""
    return os.getenv("MAPBOX_TOKEN") or MAPBOX_TOKEN


def get_ebird_api_key() -> str:
    """Return active eBird API key from environment or loaded config."""
    return os.getenv("EBIRD_API_KEY") or EBIRD_API_KEY


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
