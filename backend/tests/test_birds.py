"""Unit tests for bird services, Audubon plates, and Bird of the Day."""

import unittest
from backend.services.birds import match_audubon_species, lookup_bird_of_the_day
from backend.data.audubon_plates import AUDUBON_PLATES


class TestBirds(unittest.TestCase):
    def test_match_audubon_species_exact_scientific(self):
        plate = match_audubon_species("Cyanocitta cristata")
        self.assertIsNotNone(plate)
        self.assertEqual(plate["commonName"], "Blue Jay")
        self.assertIn("Plate CII", plate["plate"])

    def test_match_audubon_species_synonym(self):
        # Picoides pubescens is a synonym for Dryobates pubescens
        plate = match_audubon_species("Picoides pubescens")
        self.assertIsNotNone(plate)
        self.assertEqual(plate["commonName"], "Downy Woodpecker")

    def test_match_audubon_species_by_common_name(self):
        plate = match_audubon_species("", common_name="blue jay")
        self.assertIsNotNone(plate)
        self.assertEqual(plate["scientificName"], "Cyanocitta cristata")

    def test_match_audubon_species_unknown(self):
        plate = match_audubon_species("Fictionalis birdus", "Fake Bird")
        self.assertIsNone(plate)

    def test_lookup_bird_of_the_day_returns_valid_plate(self):
        botd = lookup_bird_of_the_day(lat=40.0, lon=-75.5)
        self.assertIsNotNone(botd)
        self.assertIn("commonName", botd)
        self.assertIn("scientificName", botd)
        self.assertIn("plate", botd)
        self.assertIn("proxyImageUrl", botd)
        self.assertTrue(botd["proxyImageUrl"].startswith("/api/audubon-image?species="))


if __name__ == "__main__":
    unittest.main()
