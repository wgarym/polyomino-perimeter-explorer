import unittest
from unittest.mock import patch

from perimeter_app.data import dataset_url, load_dataset


class DataTests(unittest.TestCase):
    def test_dataset_url(self):
        self.assertEqual(
            dataset_url(4, 8, 0),
            "https://wgarym.github.io/perimeter/data-4-8-0.json",
        )

    @patch("perimeter_app.data.fetch_json")
    def test_loads_all_numbered_parts(self, fetch_json):
        fetch_json.return_value = [[[1]]]
        figures = load_dataset(13, 28)
        self.assertEqual(len(figures), 4)
        self.assertEqual(fetch_json.call_count, 4)


if __name__ == "__main__":
    unittest.main()
