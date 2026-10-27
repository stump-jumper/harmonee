"""Property profile orchestration for reading, enriching, and saving address state."""

from datetime import datetime
from typing import Optional

from backend import config
from backend.services.birds import lookup_bird_of_the_day
from backend.services.ecology import lookup_ecoregions, lookup_keystone_plants
from backend.services.geocoding import lookup_suggestions
from backend.services.gis import lookup_capture_date, lookup_parcel_boundary
from backend.services.segmentation import segment_parcel_habitats
from backend.services.soil import lookup_soil_survey
from backend.storage import read_data, write_data


def get_enriched_property_data() -> dict:
    """Load persisted property profile, lazily enriching any missing or stale ecological metadata."""
    data = read_data()
    address = data.get("address", "")
    lat = data.get("lat")
    lon = data.get("lon")
    dirty = False

    if address and (lat is None or lon is None):
        matches = lookup_suggestions(address)
        if matches:
            lat = matches[0].get("lat")
            lon = matches[0].get("lon")
            data["lat"] = lat
            data["lon"] = lon
            dirty = True

    capture_date = data.get("captureDate")
    if lat is not None and lon is not None and not capture_date:
        capture_date = lookup_capture_date(lat, lon)
        if capture_date:
            data["captureDate"] = capture_date
            dirty = True

    parcel = data.get("parcel")
    if lat is not None and lon is not None and not parcel:
        parcel = lookup_parcel_boundary(lat, lon, address)
        if parcel:
            data["parcel"] = parcel
            dirty = True

    ecoregions = data.get("ecoregions")
    if lat is not None and lon is not None and (
        not isinstance(ecoregions, dict) or not ecoregions.get("description")
    ):
        ecoregions = lookup_ecoregions(lat, lon)
        if ecoregions:
            data["ecoregions"] = ecoregions
            dirty = True

    today_str = datetime.now().strftime("%Y-%m-%d")
    bird_of_the_day = data.get("birdOfTheDay")
    if lat is not None and lon is not None and (
        not isinstance(bird_of_the_day, dict)
        or bird_of_the_day.get("dateKey") != today_str
    ):
        bird_of_the_day = lookup_bird_of_the_day(lat, lon)
        if bird_of_the_day:
            data["birdOfTheDay"] = bird_of_the_day
            dirty = True

    keystone_plants = data.get("keystonePlants")
    if lat is not None and lon is not None and (
        not isinstance(keystone_plants, dict)
        or not keystone_plants.get("treesAndShrubs")
    ):
        keystone_plants = lookup_keystone_plants(lat, lon, ecoregions)
        if keystone_plants:
            data["keystonePlants"] = keystone_plants
            dirty = True

    habitat_segmentation = data.get("habitatSegmentation")
    if parcel and (
        not isinstance(habitat_segmentation, dict)
        or not habitat_segmentation.get("layers")
    ):
        habitat_segmentation = segment_parcel_habitats(parcel, config.get_mapbox_token())
        if habitat_segmentation and habitat_segmentation.get("layers"):
            data["habitatSegmentation"] = habitat_segmentation
            dirty = True

    soil_survey = data.get("soilSurvey")
    if (parcel or (lat is not None and lon is not None)) and (
        not isinstance(soil_survey, dict) or not soil_survey.get("summary")
    ):
        soil_survey = lookup_soil_survey(parcel=parcel, lat=lat, lon=lon)
        if soil_survey:
            data["soilSurvey"] = soil_survey
            dirty = True

    if dirty:
        write_data(data)

    return {
        "address": address,
        "lat": lat,
        "lon": lon,
        "captureDate": capture_date,
        "parcel": parcel,
        "ecoregions": ecoregions,
        "birdOfTheDay": bird_of_the_day,
        "keystonePlants": keystone_plants,
        "habitatSegmentation": habitat_segmentation,
        "paintStrokes": data.get("paintStrokes", []),
        "habitatObjects": data.get("habitatObjects", []),
        "soilSurvey": soil_survey,
    }


def save_and_enrich_property_address(
    address: str, lat: Optional[float] = None, lon: Optional[float] = None
) -> dict:
    """Save a new property address, enrich all GIS and ecological datasets, and persist to disk."""
    data = read_data()
    cleaned = address.strip()

    if cleaned and (lat is None or lon is None):
        matches = lookup_suggestions(cleaned)
        if matches:
            lat = matches[0].get("lat")
            lon = matches[0].get("lon")

    has_coords = lat is not None and lon is not None
    capture_date = lookup_capture_date(lat, lon) if has_coords else None
    parcel = lookup_parcel_boundary(lat, lon, cleaned) if has_coords else None
    ecoregions = lookup_ecoregions(lat, lon) if has_coords else None
    bird_of_the_day = lookup_bird_of_the_day(lat, lon) if has_coords else None
    keystone_plants = lookup_keystone_plants(lat, lon, ecoregions) if has_coords else None
    habitat_segmentation = (
        segment_parcel_habitats(parcel, config.get_mapbox_token()) if parcel else None
    )
    soil_survey = (
        lookup_soil_survey(parcel=parcel, lat=lat, lon=lon)
        if (parcel or has_coords)
        else None
    )

    data["address"] = cleaned
    data["lat"] = lat
    data["lon"] = lon
    data["captureDate"] = capture_date
    data["parcel"] = parcel
    data["ecoregions"] = ecoregions
    data["birdOfTheDay"] = bird_of_the_day
    data["keystonePlants"] = keystone_plants
    data["habitatSegmentation"] = habitat_segmentation
    data["soilSurvey"] = soil_survey
    write_data(data)

    return {
        "address": data["address"],
        "lat": data["lat"],
        "lon": data["lon"],
        "captureDate": capture_date,
        "parcel": parcel,
        "ecoregions": ecoregions,
        "birdOfTheDay": bird_of_the_day,
        "keystonePlants": keystone_plants,
        "habitatSegmentation": habitat_segmentation,
        "paintStrokes": data.get("paintStrokes", []),
        "habitatObjects": data.get("habitatObjects", []),
        "soilSurvey": soil_survey,
        "saved": True,
    }
