"""Bird imagery, feeder visitor likelihood, and eBird sightings endpoints."""

from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.schemas import FeederLikelihoodPayload
from backend.services.birds import fetch_audubon_image_bytes, fetch_bird_photo_bytes
from backend.services.ebird import clear_ebird_cache, get_ebird_sightings_data
from backend.services.feeder import (
    build_feeder_likelihood_response,
    get_feeder_options_catalog,
)
from backend.storage import read_data

router = APIRouter(prefix="/api", tags=["birds"])


@router.get("/audubon-image")
@router.get("/birds/audubon-image")
def get_audubon_image(species: str = Query(...)):
    img_bytes = fetch_audubon_image_bytes(species)
    if img_bytes:
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    return Response(status_code=404)


@router.get("/birds/photo")
def get_bird_photo(species: str = Query(...)):
    """Serve stock photography for a bird species from cache, Wikipedia, or Audubon fallback."""
    img_bytes = fetch_bird_photo_bytes(species)
    if img_bytes:
        return Response(
            content=img_bytes,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    return Response(status_code=404)


@router.get("/feeder/options")
def get_feeder_options():
    """Return available feeder food ingredients and preset seed blends."""
    return get_feeder_options_catalog()


@router.post("/feeder/likelihood")
def get_feeder_likelihood(payload: FeederLikelihoodPayload):
    """Compute probable visiting species based on location, season, and food selection."""
    data = read_data()
    lat = payload.lat if payload.lat is not None else data.get("lat")
    lon = payload.lon if payload.lon is not None else data.get("lon")
    ecoregions = data.get("ecoregions") if isinstance(data.get("ecoregions"), dict) else None

    return build_feeder_likelihood_response(
        foods=payload.foods,
        season=payload.season,
        month=payload.month,
        lat=lat,
        lon=lon,
        ecoregions=ecoregions,
    )


@router.get("/ebird/sightings")
def get_ebird_sightings(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_miles: float = 1.0,
    days: int = 30,
    refresh: bool = False,
):
    """Fetch bird sightings within radius_miles and days from eBird."""
    if refresh:
        clear_ebird_cache()
    data = read_data()
    prop_lat = lat if lat is not None else data.get("lat")
    prop_lon = lon if lon is not None else data.get("lon")
    if prop_lat is None or prop_lon is None:
        return {
            "error": "No location specified or saved in property address.",
            "sightings": [],
            "topRecent": [],
            "topClosest": [],
            "topCommon": [],
        }
    return get_ebird_sightings_data(
        prop_lat, prop_lon, radius_miles=float(radius_miles), days=int(days)
    )
