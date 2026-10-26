"""Unit tests for JSON disk storage helpers."""

import json
from pathlib import Path
import tempfile
import unittest

from backend.storage import read_data, write_data


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test_data.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_nonexistent_file_returns_empty_dict(self):
        data = read_data(self.test_file)
        self.assertEqual(data, {})

    def test_write_and_read_roundtrip(self):
        sample = {"address": "123 Main St", "lat": 40.0, "lon": -75.5}
        write_data(sample, self.test_file)
        result = read_data(self.test_file)
        self.assertEqual(result, sample)

    def test_read_corrupt_json_returns_empty_dict(self):
        self.test_file.write_text("{corrupt: json content", encoding="utf-8")
        result = read_data(self.test_file)
        self.assertEqual(result, {})

    def test_write_creates_parent_directories(self):
        nested = Path(self.temp_dir.name) / "sub" / "folder" / "data.json"
        write_data({"test": True}, nested)
        self.assertTrue(nested.exists())
        self.assertEqual(read_data(nested), {"test": True})


if __name__ == "__main__":
    unittest.main()
