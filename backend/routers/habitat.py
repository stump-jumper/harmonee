"""Habitat objects persistence and interactive parcel segmentation endpoints."""

from fastapi import APIRouter

from backend import config
from backend.schemas import HabitatObjectsPayload, PaintSegmentationPayload
from backend.services.segmentation import (
    segment_parcel_from_user_paint,
    segment_parcel_habitats,
)
from backend.storage import read_data, write_data

router = APIRouter(prefix="/api", tags=["habitat"])


@router.get("/habitat-objects")
def get_habitat_objects():
    data = read_data()
    return {"objects": data.get("habitatObjects", [])}


@router.post("/habitat-objects")
def save_habitat_objects(payload: HabitatObjectsPayload):
    data = read_data()
    data["habitatObjects"] = payload.objects
    write_data(data)
    return {"objects": data["habitatObjects"], "saved": True}


@router.post("/segment/paint")
def run_paint_segmentation(payload: PaintSegmentationPayload):
    data = read_data()
    parcel = data.get("parcel")
    if not parcel:
        return {"layers": [], "message": "No parcel boundary loaded"}
    strokes = payload.strokes
    habitat_segmentation = segment_parcel_from_user_paint(
        parcel, strokes, config.get_mapbox_token()
    )
    data["paintStrokes"] = strokes
    data["habitatSegmentation"] = habitat_segmentation
    write_data(data)
    return habitat_segmentation


@router.post("/segment")
def run_segmentation():
    data = read_data()
    parcel = data.get("parcel")
    if not parcel:
        return {"layers": []}
    existing_strokes = data.get("paintStrokes", [])
    mapbox_token = config.get_mapbox_token()
    if existing_strokes:
        habitat_segmentation = segment_parcel_from_user_paint(
            parcel, existing_strokes, mapbox_token
        )
    else:
        habitat_segmentation = segment_parcel_habitats(parcel, mapbox_token)
    data["habitatSegmentation"] = habitat_segmentation
    write_data(data)
    return habitat_segmentation
