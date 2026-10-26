"""Unit tests for iNaturalist property observation integration, spatial filtering, and router endpoints."""

import unittest
from unittest.mock import patch

from backend import config
from backend.schemas import InaturalistUsernamePayload
from backend.services.inaturalist import (
    calculate_distance_miles,
    check_point_in_parcel,
    clear_inaturalist_cache,
    generate_property_inaturalist_observations,
    get_property_inaturalist_data,
    get_stored_inaturalist_username,
    save_inaturalist_username,
)
from backend.routers import inaturalist as inat_router


class TestInaturalist(unittest.TestCase):
    def setUp(self):
        clear_inaturalist_cache()
        self.sample_parcel = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-75.557, 40.630],
                        [-75.555, 40.630],
                        [-75.555, 40.633],
                        [-75.557, 40.633],
                        [-75.557, 40.630],
                    ]
                ],
            },
            "properties": {"PARCEL_ID": "TEST-123"},
        }

    def test_01_check_point_in_parcel(self):
        # Point inside sample polygon
        inside = check_point_in_parcel(40.6315, -75.5560, self.sample_parcel)
        self.assertTrue(inside)

        # Point well outside polygon
        outside = check_point_in_parcel(40.7000, -75.5000, self.sample_parcel)
        self.assertFalse(outside)

        # None parcel
        self.assertFalse(check_point_in_parcel(40.6315, -75.5560, None))

    def test_02_calculate_distance_miles(self):
        d0 = calculate_distance_miles(40.0, -75.0, 40.0, -75.0)
        self.assertEqual(d0, 0.0)

        d = calculate_distance_miles(40.63, -75.55, 40.64, -75.55)
        self.assertGreater(d, 0.6)
        self.assertLess(d, 0.8)

    def test_03_generate_property_observations(self):
        lat = 40.6316
        lon = -75.5565
        obs_list = generate_property_inaturalist_observations(
            lat, lon, parcel=self.sample_parcel, username="nature_lover"
        )
        self.assertIsInstance(obs_list, list)
        self.assertTrue(len(obs_list) > 0)

        first = obs_list[0]
        self.assertIn("id", first)
        self.assertIn("speciesGuess", first)
        self.assertIn("taxon", first)
        self.assertIn("iconicTaxonName", first["taxon"])
        self.assertIn("photoUrl", first["taxon"])
        self.assertIn("qualityGrade", first)
        self.assertIn("isResearchGrade", first)
        self.assertIn("insideProperty", first)
        self.assertIn("distanceMiles", first)
        self.assertIn("user", first)
        self.assertEqual(first["user"]["login"], "nature_lover")
        self.assertIn("photos", first)
        self.assertIn("uri", first)

        # Ensure on-property observations exist
        on_prop = [o for o in obs_list if o["insideProperty"]]
        self.assertTrue(len(on_prop) > 0)

    def test_04_get_property_inaturalist_data_aggregation(self):
        lat = 40.6316
        lon = -75.5565
        res = get_property_inaturalist_data(
            lat=lat,
            lon=lon,
            parcel=self.sample_parcel,
            username="troxellp",
            property_only=True,
        )

        self.assertIn("observations", res)
        self.assertIn("totalObservations", res)
        self.assertIn("speciesCount", res)
        self.assertIn("researchGradeCount", res)
        self.assertIn("researchGradePercent", res)
        self.assertIn("iconicTaxaCounts", res)
        self.assertIn("observer", res)
        self.assertIn("source", res)

        self.assertTrue(res["totalObservations"] > 0)
        self.assertTrue(res["speciesCount"] > 0)
        self.assertGreaterEqual(res["researchGradePercent"], 0.0)

        # Taxa counts
        counts = res["iconicTaxaCounts"]
        self.assertIn("Plantae", counts)
        self.assertIn("Insecta", counts)

    def test_05_category_filtering(self):
        lat = 40.6316
        lon = -75.5565
        plants_res = get_property_inaturalist_data(
            lat=lat,
            lon=lon,
            parcel=self.sample_parcel,
            property_only=False,
            radius_miles=0.5,
            taxon="Plantae",
        )
        for obs in plants_res["observations"]:
            self.assertEqual(obs["taxon"]["iconicTaxonName"], "Plantae")

        insects_res = get_property_inaturalist_data(
            lat=lat,
            lon=lon,
            parcel=self.sample_parcel,
            property_only=False,
            radius_miles=0.5,
            taxon="Insecta",
        )
        for obs in insects_res["observations"]:
            self.assertEqual(obs["taxon"]["iconicTaxonName"], "Insecta")

    @patch("backend.services.inaturalist.read_data")
    @patch("backend.services.inaturalist.write_data")
    def test_06_username_persistence(self, mock_write, mock_read):
        mock_read.return_value = {"inaturalistUsername": "old_user"}
        self.assertEqual(get_stored_inaturalist_username(), "old_user")

        res = save_inaturalist_username("new_naturalist")
        self.assertTrue(res["saved"])
        self.assertEqual(res["username"], "new_naturalist")
        mock_write.assert_called_once()

    @patch("backend.routers.inaturalist.read_data")
    def test_07_router_observations_endpoint(self, mock_read):
        mock_read.return_value = {
            "lat": 40.6316,
            "lon": -75.5565,
            "parcel": self.sample_parcel,
            "inaturalistUsername": "steward",
        }
        res = inat_router.get_inaturalist_observations()
        self.assertIn("observations", res)
        self.assertTrue(res["totalObservations"] > 0)

    @patch("backend.routers.inaturalist.read_data")
    def test_08_router_no_location(self, mock_read):
        mock_read.return_value = {}
        res = inat_router.get_inaturalist_observations()
        self.assertIn("error", res)
        self.assertEqual(res["observations"], [])

    @patch("backend.routers.inaturalist.save_inaturalist_username")
    def test_09_router_username_endpoints(self, mock_save):
        mock_save.return_value = {"saved": True, "username": "test_user"}
        payload = InaturalistUsernamePayload(username="test_user")
        res = inat_router.update_username(payload)
        self.assertEqual(res["username"], "test_user")

    def test_10_jwt_token_decoding(self):
        user_id = config.get_inaturalist_user_id()
        self.assertEqual(user_id, 6237437)


if __name__ == "__main__":
    unittest.main()
