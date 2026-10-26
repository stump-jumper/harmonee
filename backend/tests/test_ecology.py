"""Unit tests for ecoregion and keystone plant services."""

import unittest
from backend.services.ecology import (
    format_ecoregion_name,
    describe_level4,
    lookup_keystone_plants,
)
from backend.data.ecoregion_data import LEVEL_IV_DESCRIPTIONS
from backend.data.keystone_plants import KEYSTONE_PLANT_DATASET


class TestEcology(unittest.TestCase):
    def test_format_ecoregion_name(self):
        self.assertEqual(format_ecoregion_name("EASTERN TEMPERATE FORESTS"), "Eastern Temperate Forests")
        self.assertEqual(format_ecoregion_name("PIEDMONT"), "Piedmont")
        self.assertEqual(format_ecoregion_name(""), "")
        self.assertEqual(format_ecoregion_name(None), "")
        self.assertEqual(format_ecoregion_name("Already Mixed Case"), "Already Mixed Case")

    def test_describe_level4_catalog_lookup(self):
        desc = describe_level4("64a", "Northern Piedmont", "Piedmont", "Eastern Temperate Forests")
        self.assertEqual(desc, LEVEL_IV_DESCRIPTIONS["64a"])

    def test_describe_level4_fallback(self):
        desc = describe_level4("999z", "Custom Valley", "Custom Hills", "Temperate Zone")
        self.assertIn("Custom Valley", desc)
        self.assertIn("Custom Hills", desc)

    def test_keystone_plant_dataset_structure(self):
        self.assertIn("8", KEYSTONE_PLANT_DATASET)
        profile = KEYSTONE_PLANT_DATASET["8"]
        self.assertIn("treesAndShrubs", profile)
        self.assertIn("flowersAndGrasses", profile)
        self.assertTrue(len(profile["treesAndShrubs"]) > 0)
        self.assertTrue(len(profile["flowersAndGrasses"]) > 0)

        first_tree = profile["treesAndShrubs"][0]
        self.assertIn("genus", first_tree)
        self.assertIn("commonName", first_tree)
        self.assertIn("lepidopteraCount", first_tree)

    def test_lookup_keystone_plants(self):
        result = lookup_keystone_plants(lat=40.0, lon=-75.5)
        self.assertIn("treesAndShrubs", result)
        self.assertIn("flowersAndGrasses", result)
        self.assertIn("methodology", result)
        self.assertEqual(len(result["treesAndShrubs"]), 3)
        self.assertEqual(len(result["flowersAndGrasses"]), 3)


if __name__ == "__main__":
    unittest.main()
