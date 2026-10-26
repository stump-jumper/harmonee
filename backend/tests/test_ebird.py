"""Unit tests for eBird distance calculation and observation aggregation."""

import unittest
from backend.services.ebird import (
    calculate_distance_miles,
    generate_local_ebird_observations,
    get_ebird_sightings_data,
    clear_ebird_cache,
)


class TestEBird(unittest.TestCase):
    def setUp(self):
        clear_ebird_cache()

    def test_calculate_distance_miles(self):
        d0 = calculate_distance_miles(40.0, -75.0, 40.0, -75.0)
        self.assertAlmostEqual(d0, 0.0, places=3)

        d_lat = calculate_distance_miles(40.0, -75.0, 41.0, -75.0)
        self.assertGreater(d_lat, 68.0)
        self.assertLess(d_lat, 70.0)

    def test_generate_local_ebird_observations(self):
        lat = 39.96
        lon = -75.60
        observations = generate_local_ebird_observations(lat, lon, radius_miles=0.5, days=30)
        self.assertIsInstance(observations, list)
        self.assertTrue(len(observations) > 0)

        first = observations[0]
        self.assertIn("comName", first)
        self.assertIn("sciName", first)
        self.assertIn("lat", first)
        self.assertIn("lng", first)
        self.assertIn("distanceMiles", first)
        self.assertIn("audubonImage", first)
        self.assertIn("audubonPlate", first)
        self.assertIn("howMany", first)
        self.assertIn("obsDt", first)

    def test_get_ebird_sightings_data(self):
        lat = 39.96
        lon = -75.60
        result = get_ebird_sightings_data(lat, lon, radius_miles=1.0, days=30)
        self.assertIn("sightings", result)
        self.assertIn("topRecent", result)
        self.assertIn("topClosest", result)
        self.assertIn("topCommon", result)
        self.assertIn("totalSightings", result)
        self.assertIn("uniqueSpeciesCount", result)
        self.assertTrue(result["uniqueSpeciesCount"] > 0)


if __name__ == "__main__":
    unittest.main()
