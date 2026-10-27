"""Unit tests for USDA Web Soil Survey service and endpoints."""

import json
import unittest
from unittest.mock import MagicMock, patch

from backend.services.soil import (
    build_aoi_wkt,
    lookup_soil_survey,
    query_sda_soil_mapunits,
)


class TestSoilService(unittest.TestCase):
    def setUp(self):
        self.sample_parcel = {
            "type": "Feature",
            "properties": {"PARCEL_ID": "12345"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-75.557, 40.631],
                        [-75.555, 40.631],
                        [-75.555, 40.633],
                        [-75.557, 40.633],
                        [-75.557, 40.631],
                    ]
                ],
            },
        }

    def test_build_aoi_wkt(self):
        wkt = build_aoi_wkt(-75.55, 40.63, -75.54, 40.64)
        self.assertTrue(wkt.startswith("POLYGON(("))
        self.assertTrue(wkt.endswith("))"))
        self.assertIn("-75.55 40.63", wkt)
        self.assertIn("-75.54 40.64", wkt)

    def test_lookup_soil_survey_no_input(self):
        result = lookup_soil_survey(parcel=None, lat=None, lon=None)
        self.assertIsNone(result)

    @patch("backend.services.soil.query_sda_soil_mapunits")
    def test_lookup_soil_survey_empty_sda(self, mock_query):
        mock_query.return_value = []
        result = lookup_soil_survey(parcel=self.sample_parcel)
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], [])
        self.assertEqual(result["geojson"]["features"], [])
        self.assertEqual(result["labelsGeojson"]["features"], [])

    @patch("backend.services.soil.query_sda_soil_mapunits")
    def test_lookup_soil_survey_success(self, mock_query):
        # Two map units splitting the sample parcel
        mock_query.return_value = [
            {
                "mukey": "1001",
                "musym": "DbB",
                "muname": "Duffield silt loam, 3 to 8 percent slopes",
                "geom_wkt": "POLYGON((-75.557 40.631, -75.556 40.631, -75.556 40.633, -75.557 40.633, -75.557 40.631))",
            },
            {
                "mukey": "1002",
                "musym": "WaC",
                "muname": "Washington silt loam, 8 to 15 percent slopes",
                "geom_wkt": "POLYGON((-75.556 40.631, -75.555 40.631, -75.555 40.633, -75.556 40.633, -75.556 40.631))",
            },
        ]

        result = lookup_soil_survey(parcel=self.sample_parcel)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["summary"]), 2)
        
        symbols = [item["musym"] for item in result["summary"]]
        self.assertIn("DbB", symbols)
        self.assertIn("WaC", symbols)

        # Total coverage should sum to 100%
        total_pct = sum(item["percentage"] for item in result["summary"])
        self.assertAlmostEqual(total_pct, 100.0, places=1)

        # Polygon features
        features = result["geojson"]["features"]
        self.assertEqual(len(features), 2)
        for feat in features:
            self.assertIn("musym", feat["properties"])
            self.assertIn("muname", feat["properties"])
            self.assertIn("percentage", feat["properties"])
            self.assertIn("color", feat["properties"])

        # Map unit symbol labels centered within each map unit
        labels = result["labelsGeojson"]["features"]
        self.assertEqual(len(labels), 2)
        for lbl in labels:
            self.assertEqual(lbl["geometry"]["type"], "Point")
            coords = lbl["geometry"]["coordinates"]
            self.assertEqual(len(coords), 2)
            self.assertGreaterEqual(coords[0], -75.557)
            self.assertLessEqual(coords[0], -75.555)
            self.assertGreaterEqual(coords[1], 40.631)
            self.assertLessEqual(coords[1], 40.633)

    @patch("backend.services.soil.urllib.request.urlopen")
    def test_query_sda_soil_mapunits_parses_table(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "Table": [
                ["mukey", "musym", "muname", "geom_wkt"],
                ["543135", "DbB", "Duffield silt loam", "POLYGON((-75.55 40.63, -75.54 40.63, -75.54 40.64, -75.55 40.64, -75.55 40.63))"],
            ]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        records = query_sda_soil_mapunits("POLYGON((-75.55 40.63, -75.54 40.63, -75.54 40.64, -75.55 40.64, -75.55 40.63))")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["musym"], "DbB")
        self.assertEqual(records[0]["mukey"], "543135")
