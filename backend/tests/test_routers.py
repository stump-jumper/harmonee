"""Unit tests for FastAPI router endpoints and request schemas."""

import unittest
from unittest.mock import patch

from backend.schemas import (
    AddressPayload,
    HabitatObjectsPayload,
    PaintSegmentationPayload,
    FeederLikelihoodPayload,
)
from backend.routers import health, property, habitat, birds


class TestRouters(unittest.TestCase):
    def test_01_health_check(self):
        res = health.health_check()
        self.assertEqual(res, {"status": "ok"})

    def test_02_supported_counties(self):
        res = property.get_supported_counties()
        self.assertIn("counties", res)
        self.assertIn("supportedCountyNames", res)
        self.assertIn("Montgomery County", res["supportedCountyNames"])
        self.assertIn("Lehigh County", res["supportedCountyNames"])

    def test_03_autocomplete_address_too_short(self):
        res = property.autocomplete_address(q="ab")
        self.assertEqual(res, {"suggestions": []})

    @patch("backend.routers.property.lookup_suggestions")
    def test_04_autocomplete_address_valid(self, mock_lookup):
        mock_lookup.return_value = [{"label": "100 Main St, Allentown, PA", "lat": 40.6, "lon": -75.48}]
        res = property.autocomplete_address(q="Allentown")
        self.assertEqual(len(res["suggestions"]), 1)
        self.assertEqual(res["suggestions"][0]["label"], "100 Main St, Allentown, PA")

    @patch("backend.routers.property.get_enriched_property_data")
    def test_05_get_address(self, mock_get_enriched):
        mock_get_enriched.return_value = {"address": "123 Main St", "lat": 40.0, "lon": -75.5}
        res = property.get_address()
        self.assertEqual(res["address"], "123 Main St")

    @patch("backend.routers.property.save_and_enrich_property_address")
    def test_06_save_address(self, mock_save):
        mock_save.return_value = {"address": "456 Oak Rd", "lat": 40.1, "lon": -75.4}
        payload = AddressPayload(address="456 Oak Rd", lat=40.1, lon=-75.4)
        res = property.save_address(payload)
        self.assertEqual(res["address"], "456 Oak Rd")
        mock_save.assert_called_once_with(address="456 Oak Rd", lat=40.1, lon=-75.4)

    @patch("backend.routers.property.lookup_capture_date")
    def test_07_get_imagery_date(self, mock_date):
        mock_date.return_value = "Sep 15, 2024"
        res = property.get_imagery_date(lat=40.6, lon=-75.48)
        self.assertEqual(res, {"captureDate": "Sep 15, 2024"})

    @patch("backend.routers.habitat.read_data")
    def test_08_get_habitat_objects(self, mock_read):
        mock_read.return_value = {"habitatObjects": [{"id": "feeder-1", "type": "feeder"}]}
        res = habitat.get_habitat_objects()
        self.assertEqual(len(res["objects"]), 1)
        self.assertEqual(res["objects"][0]["id"], "feeder-1")

    @patch("backend.routers.habitat.write_data")
    @patch("backend.routers.habitat.read_data")
    def test_09_save_habitat_objects(self, mock_read, mock_write):
        mock_read.return_value = {}
        payload = HabitatObjectsPayload(objects=[{"id": "nest-1", "type": "nestbox"}])
        res = habitat.save_habitat_objects(payload)
        self.assertTrue(res["saved"])
        self.assertEqual(len(res["objects"]), 1)
        mock_write.assert_called_once()

    @patch("backend.routers.habitat.read_data")
    def test_10_run_segmentation_without_parcel(self, mock_read):
        mock_read.return_value = {}
        res = habitat.run_segmentation()
        self.assertEqual(res, {"layers": []})

    @patch("backend.routers.habitat.read_data")
    def test_11_run_paint_segmentation_without_parcel(self, mock_read):
        mock_read.return_value = {}
        payload = PaintSegmentationPayload(strokes=[])
        res = habitat.run_paint_segmentation(payload)
        self.assertEqual(res["layers"], [])
        self.assertIn("No parcel boundary", res["message"])

    def test_12_feeder_options(self):
        res = birds.get_feeder_options()
        self.assertIn("foods", res)
        self.assertIn("presets", res)
        food_ids = [f["id"] for f in res["foods"]]
        self.assertIn("sunflower_black_oil", food_ids)

    def test_13_feeder_likelihood(self):
        payload = FeederLikelihoodPayload(
            foods=["sunflower_black_oil"],
            feederType="hopper",
            ecoregions={"level1": "8_eastern_temperate_forests"},
            month=5,
        )
        res = birds.get_feeder_likelihood(payload)
        self.assertIn("visitors", res)
        self.assertIn("totalSpecies", res)
        self.assertIn("season", res)
        self.assertEqual(res["season"], "spring")
        self.assertGreater(res["totalSpecies"], 0)

    def test_14_ebird_sightings(self):
        res = birds.get_ebird_sightings(lat=40.0, lon=-75.5, radius_miles=1.0, days=30)
        self.assertIn("sightings", res)
        self.assertIn("topRecent", res)
        self.assertIn("topClosest", res)
        self.assertIn("topCommon", res)
        self.assertGreater(len(res["sightings"]), 0)

    @patch("backend.routers.birds.fetch_audubon_image_bytes")
    def test_15_audubon_image_found(self, mock_fetch):
        mock_fetch.return_value = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        res = birds.get_audubon_image(species="Cyanocitta cristata")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.media_type, "image/jpeg")

    @patch("backend.routers.birds.fetch_audubon_image_bytes")
    def test_16_audubon_image_not_found(self, mock_fetch):
        mock_fetch.return_value = None
        res = birds.get_audubon_image(species="UnknownBird")
        self.assertEqual(res.status_code, 404)

    @patch("backend.routers.birds.fetch_bird_photo_bytes")
    def test_17_bird_photo_found(self, mock_fetch):
        mock_fetch.return_value = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        res = birds.get_bird_photo(species="Cyanocitta cristata")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.media_type, "image/jpeg")

    @patch("backend.routers.birds.fetch_bird_photo_bytes")
    def test_18_bird_photo_not_found(self, mock_fetch):
        mock_fetch.return_value = None
        res = birds.get_bird_photo(species="UnknownBird")
        self.assertEqual(res.status_code, 404)

    @patch("backend.routers.property.read_data")
    def test_19_soil_survey_cached(self, mock_read):
        mock_read.return_value = {
            "soilSurvey": {
                "summary": [{"musym": "DbB", "muname": "Duffield silt loam", "percentage": 100.0}],
                "geojson": {"type": "FeatureCollection", "features": []},
                "labelsGeojson": {"type": "FeatureCollection", "features": []},
            }
        }
        res = property.get_soil_survey()
        self.assertIn("summary", res)
        self.assertEqual(len(res["summary"]), 1)
        self.assertEqual(res["summary"][0]["musym"], "DbB")


if __name__ == "__main__":
    unittest.main()
