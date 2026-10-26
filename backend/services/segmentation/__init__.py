"""Interactive parcel-bounded habitat segmentation package."""

from backend.services.segmentation.classifier import (
    HABITAT_CLASSES,
    HABITAT_LOOKUP,
    fetch_satellite_patch,
    segment_parcel_from_user_paint,
    segment_parcel_habitats,
)

__all__ = [
    "HABITAT_CLASSES",
    "HABITAT_LOOKUP",
    "fetch_satellite_patch",
    "segment_parcel_from_user_paint",
    "segment_parcel_habitats",
]
