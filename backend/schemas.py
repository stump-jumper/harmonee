"""Pydantic request schemas for Harmonee API endpoints."""

from typing import Optional
from pydantic import BaseModel


class AddressPayload(BaseModel):
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class HabitatObjectsPayload(BaseModel):
    objects: list = []


class PaintSegmentationPayload(BaseModel):
    strokes: list = []


class FeederLikelihoodPayload(BaseModel):
    foods: list[str] = []
    season: Optional[str] = None
    month: Optional[int] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
