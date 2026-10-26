"""Property address, geocoding autocomplete, supported counties, and imagery metadata endpoints."""

from fastapi import APIRouter, Query

from backend import config
from backend.schemas import AddressPayload
from backend.services.geocoding import lookup_suggestions
from backend.services.gis import lookup_capture_date
from backend.services.property_service import (
    get_enriched_property_data,
    save_and_enrich_property_address,
)

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
