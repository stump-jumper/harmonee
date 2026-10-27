"""Property address, geocoding autocomplete, supported counties, imagery metadata, and soil survey endpoints."""

from fastapi import APIRouter, Query

from backend import config
from backend.schemas import AddressPayload
from backend.services.geocoding import lookup_suggestions
from backend.services.gis import lookup_capture_date
from backend.services.property_service import (
    get_enriched_property_data,
    save_and_enrich_property_address,
)
from backend.services.soil import lookup_soil_survey
from backend.storage import read_data, write_data

router = APIRouter(prefix="/api", tags=["property"])


@router.get("/address")
def get_address():
    return get_enriched_property_data()


@router.post("/address")
def save_address(payload: AddressPayload):
    return save_and_enrich_property_address(
        address=payload.address,
        lat=payload.lat,
        lon=payload.lon,
    )


@router.get("/address/autocomplete")
def autocomplete_address(q: str = ""):
    query = (str(q.default) if hasattr(q, "default") else str(q)).strip()
    if len(query) < 3:
        return {"suggestions": []}
    return {"suggestions": lookup_suggestions(query)}


@router.get("/supported-counties")
def get_supported_counties():
    return {
        "counties": config.SUPPORTED_COUNTIES,
        "supportedCountyNames": [c["name"] for c in config.SUPPORTED_COUNTIES],
    }


@router.get("/imagery-date")
def get_imagery_date(lat: float, lon: float):
    return {"captureDate": lookup_capture_date(float(lat), float(lon))}


@router.get("/soil-survey")
def get_soil_survey():
    """Retrieve USDA Web Soil Survey data for the current property."""
    data = read_data()
    soil = data.get("soilSurvey")
    if soil and isinstance(soil, dict) and soil.get("summary"):
        return soil
    parcel = data.get("parcel")
    lat = data.get("lat")
    lon = data.get("lon")
    result = lookup_soil_survey(parcel=parcel, lat=lat, lon=lon)
    if result:
        data["soilSurvey"] = result
        write_data(data)
        return result
    return {
        "source": "USDA Web Soil Survey (Soil Data Access)",
        "summary": [],
        "geojson": {"type": "FeatureCollection", "features": []},
        "labelsGeojson": {"type": "FeatureCollection", "features": []},
    }
