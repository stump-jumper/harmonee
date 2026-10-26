"""iNaturalist property biodiversity observations and settings API endpoints."""

from typing import Optional
from fastapi import APIRouter

from backend.schemas import InaturalistUsernamePayload
from backend.services.inaturalist import (
    clear_inaturalist_cache,
    get_property_inaturalist_data,
    get_stored_inaturalist_username,
    save_inaturalist_username,
)
from backend.storage import read_data

router = APIRouter(prefix="/api/inaturalist", tags=["inaturalist"])


@router.get("/observations")
def get_inaturalist_observations(
    username: Optional[str] = None,
    property_only: bool = True,
    radius_miles: float = 0.5,
    scope: str = "property",
    taxon: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    refresh: bool = False,
):
    """Retrieve iNaturalist observations recorded on or near the property parcel."""
    if refresh:
        clear_inaturalist_cache()

    data = read_data()
    prop_lat = lat if lat is not None else data.get("lat")
    prop_lon = lon if lon is not None else data.get("lon")
    parcel = data.get("parcel")

    if prop_lat is None or prop_lon is None:
        return {
            "error": "No location specified or saved in property address.",
            "observations": [],
            "totalObservations": 0,
            "speciesCount": 0,
            "researchGradeCount": 0,
            "researchGradePercent": 0,
            "iconicTaxaCounts": {},
            "observer": {"login": "", "isConfigured": False, "tokenConfigured": False},
        }

    return get_property_inaturalist_data(
        lat=float(prop_lat),
        lon=float(prop_lon),
        parcel=parcel,
        username=username,
        property_only=bool(property_only),
        radius_miles=float(radius_miles),
        scope=scope,
        taxon=taxon,
    )


@router.get("/username")
def get_username():
    """Get active or saved iNaturalist username."""
    return {"username": get_stored_inaturalist_username()}


@router.post("/username")
def update_username(payload: InaturalistUsernamePayload):
    """Save user iNaturalist username to property settings."""
    return save_inaturalist_username(payload.username)
