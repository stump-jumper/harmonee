"""Unit tests for geocoding formatting and county filtering."""

import unittest
from backend.services.geocoding import (
    format_photon_feature,
    extract_mapbox_county,
    extract_photon_county,
)


class TestGeocoding(unittest.TestCase):
    def test_format_photon_feature_complete(self):
        feat = {
            "properties": {
                "housenumber": "500",
                "street": "Highland Ave",
                "city": "Allentown",
                "state": "Pennsylvania",
                "postcode": "18102",
                "country": "United States",
            },
            "geometry": {"coordinates": [-75.48, 40.60]},
        }
        res = format_photon_feature(feat, county="Lehigh County")
        self.assertIsNotNone(res)
        self.assertEqual(res["label"], "500 Highland Ave, Allentown, Pennsylvania, 18102, United States")
        self.assertEqual(res["lat"], 40.60)
        self.assertEqual(res["lon"], -75.48)
        self.assertEqual(res["county"], "Lehigh County")

    def test_format_photon_feature_minimal(self):
        feat = {
            "properties": {"city": "Norristown", "state": "PA"},
            "geometry": {"coordinates": [-75.34, 40.12]},
        }
        res = format_photon_feature(feat)
        self.assertIsNotNone(res)
        self.assertEqual(res["label"], "Norristown, PA")
        self.assertNotIn("county", res)

    def test_format_photon_feature_empty_returns_none(self):
        feat = {"properties": {}, "geometry": {"coordinates": []}}
        self.assertIsNone(format_photon_feature(feat))

    def test_extract_mapbox_county_supported(self):
        feat = {
            "context": [
                {"id": "district.123", "text": "Lehigh County"},
                {"id": "region.456", "text": "Pennsylvania"},
            ]
        }
        self.assertEqual(extract_mapbox_county(feat), "Lehigh County")

        feat2 = {
            "context": [
                {"id": "district.789", "text": "Montgomery County"},
                {"id": "region.456", "text": "PA"},
            ]
        }
        self.assertEqual(extract_mapbox_county(feat2), "Montgomery County")

    def test_extract_mapbox_county_unsupported(self):
        feat = {
            "context": [
                {"id": "district.111", "text": "Kings County"},
                {"id": "region.222", "text": "New York"},
            ]
        }
        self.assertIsNone(extract_mapbox_county(feat))

    def test_extract_photon_county(self):
        feat_lehigh = {
            "properties": {
                "county": "Lehigh County",
                "state": "Pennsylvania",
                "country": "United States",
            }
        }
        self.assertEqual(extract_photon_county(feat_lehigh), "Lehigh County")

        feat_montgomery = {
            "properties": {
                "county": "Montgomery",
                "state": "pa",
                "country": "usa",
            }
        }
        self.assertEqual(extract_photon_county(feat_montgomery), "Montgomery County")

        feat_other = {
            "properties": {
                "county": "Erie",
                "state": "PA",
                "country": "United States",
            }
        }
        self.assertIsNone(extract_photon_county(feat_other))


if __name__ == "__main__":
    unittest.main()
