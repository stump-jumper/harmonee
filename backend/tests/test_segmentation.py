"""Unit tests for habitat segmentation geometry algorithms."""

import unittest
import numpy as np
from shapely.geometry import Polygon, box

from backend.services.segmentation.geometry import (
    clean_polygonal,
    merge_small_regions,
    catmull_rom_spline_ring,
)


class TestSegmentationGeometry(unittest.TestCase):
    def test_clean_polygonal_valid_box(self):
        b = box(0.0, 0.0, 1.0, 1.0)
        cleaned = clean_polygonal(b, min_area=0.01)
        self.assertTrue(cleaned.is_valid)
        self.assertAlmostEqual(cleaned.area, 1.0, places=2)

    def test_clean_polygonal_filters_micro_slivers(self):
        sliver = box(0.0, 0.0, 0.0000001, 0.0000001)
        cleaned = clean_polygonal(sliver, min_area=0.01)
        self.assertTrue(cleaned.is_empty)

    def test_clean_polygonal_none_or_empty(self):
        self.assertTrue(clean_polygonal(None).is_empty)
        self.assertTrue(clean_polygonal(Polygon()).is_empty)

    def test_merge_small_regions(self):
        labels = np.ones((5, 5), dtype=np.int32)
        labels[2, 2] = 2
        valid_mask = np.ones((5, 5), dtype=bool)

        merged = merge_small_regions(labels, valid_mask, min_pixels=3)
        self.assertEqual(merged[2, 2], 1)
        self.assertTrue(np.all(merged == 1))

    def test_catmull_rom_spline_ring(self):
        pts = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        smoothed = catmull_rom_spline_ring(pts, subdivisions=3)
        self.assertIsInstance(smoothed, list)
        self.assertGreater(len(smoothed), len(pts))
        self.assertEqual(smoothed[0], smoothed[-1])


if __name__ == "__main__":
    unittest.main()
