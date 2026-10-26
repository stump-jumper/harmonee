"""Unit tests for feeder visitor calculation and season/ecoregion normalization."""

import unittest
from backend.services.feeder import (
    get_season_for_month,
    normalize_ecoregion_zone,
    calculate_feeder_likelihood,
    build_feeder_likelihood_response,
)
from backend.data.feeder_foods import FEEDER_FOODS, PRESET_FOOD_BLENDS


class TestFeeder(unittest.TestCase):
    def test_get_season_for_month(self):
        self.assertEqual(get_season_for_month(1), "winter")
        self.assertEqual(get_season_for_month(2), "winter")
        self.assertEqual(get_season_for_month(3), "spring")
        self.assertEqual(get_season_for_month(5), "spring")
        self.assertEqual(get_season_for_month(6), "summer")
        self.assertEqual(get_season_for_month(8), "summer")
        self.assertEqual(get_season_for_month(9), "fall")
        self.assertEqual(get_season_for_month(11), "fall")
        self.assertEqual(get_season_for_month(12), "winter")

    def test_normalize_ecoregion_zone_from_dict(self):
        zone = normalize_ecoregion_zone({"level1": "8.0 EASTERN TEMPERATE FORESTS"})
        self.assertEqual(zone, "8_eastern_temperate_forests")

        zone2 = normalize_ecoregion_zone({"level1": "NORTHERN FORESTS"})
        self.assertEqual(zone2, "5_northern_forests")

    def test_normalize_ecoregion_zone_from_coordinates(self):
        zone = normalize_ecoregion_zone(None, lat=40.0, lon=-75.5)
        self.assertEqual(zone, "8_eastern_temperate_forests")

        zone_pnw = normalize_ecoregion_zone(None, lat=47.6, lon=-122.3)
        self.assertEqual(zone_pnw, "7_marine_west_coast")

    def test_calculate_feeder_likelihood(self):
        foods = ["sunflower_black_oil", "suet"]
        visitors = calculate_feeder_likelihood(
            foods=foods,
            season="spring",
            ecoregion_zone="8_eastern_temperate_forests",
        )
        self.assertIsInstance(visitors, list)
        self.assertTrue(len(visitors) > 0)

        top = visitors[0]
        self.assertIn("commonName", top)
        self.assertIn("scientificName", top)
        self.assertIn("probability", top)
        self.assertIn("tier", top)
        self.assertIn(top["tier"], ["Very Likely", "Likely", "Occasional", "Uncommon / Rare"])
        self.assertGreaterEqual(top["probability"], 0.0)
        self.assertLessEqual(top["probability"], 1.0)

    def test_build_feeder_likelihood_response(self):
        resp = build_feeder_likelihood_response(
            foods=["sunflower_black_oil"],
            month=5,
            lat=40.0,
            lon=-75.5,
        )
        self.assertEqual(resp["season"], "spring")
        self.assertIn("visitors", resp)
        self.assertIn("totalSpecies", resp)
        self.assertGreater(resp["totalSpecies"], 0)

    def test_preset_food_blends_defined(self):
        self.assertIn("premium_songbird", PRESET_FOOD_BLENDS)
        self.assertIn("finch_special", PRESET_FOOD_BLENDS)
        for blend_id, blend_data in PRESET_FOOD_BLENDS.items():
            for item in blend_data["foods"]:
                self.assertIn(item, FEEDER_FOODS)


if __name__ == "__main__":
    unittest.main()
