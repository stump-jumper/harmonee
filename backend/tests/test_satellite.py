"""Unit tests for satellite layers service and router endpoint."""

import unittest
from unittest.mock import MagicMock, patch

from backend.routers import property as property_router
from backend.services.satellite import (
    DEFAULT_TEST_LAYERS,
    query_recent_satellite_layers,
)


class TestSatelliteLayers(unittest.TestCase):
    def test_default_test_layers_exist(self):
        self.assertEqual(len(DEFAULT_TEST_LAYERS), 5)
        layer_ids = [l["id"] for l in DEFAULT_TEST_LAYERS]
        self.assertNotIn("satellite-sentinel2", layer_ids)
        self.assertNotIn("satellite-landsat", layer_ids)
        self.assertNotIn("satellite-usgs-tnm", layer_ids)
        self.assertIn("satellite-naip", layer_ids)
        self.assertIn("satellite-naip-cir", layer_ids)
        self.assertIn("satellite-pema-leafoff", layer_ids)
        self.assertIn("satellite-lidar-hillshade", layer_ids)
        self.assertIn("satellite-esri-wayback", layer_ids)

    def test_query_recent_satellite_layers_fallback(self):
        # Even with failed network calls, it gracefully returns all layers
        layers = query_recent_satellite_layers(40.631667, -75.556515)
        self.assertEqual(len(layers), 5)
        for layer in layers:
            self.assertTrue(layer["tileUrl"].startswith("http"))
            self.assertIn("layerId", layer)
            self.assertIn("sourceId", layer)

    @patch("backend.routers.property.query_recent_satellite_layers")
    def test_get_satellite_layers_endpoint(self, mock_query):
        mock_query.return_value = DEFAULT_TEST_LAYERS
        res = property_router.get_satellite_layers(lat=40.63, lon=-75.55)
        self.assertIn("layers", res)
        self.assertEqual(len(res["layers"]), 5)
        mock_query.assert_called_once_with(40.63, -75.55)


if __name__ == "__main__":
    unittest.main()
