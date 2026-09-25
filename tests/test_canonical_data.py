import unittest
from unittest.mock import patch

from perimeter_app.canonical_data import (
    CollectionManifest,
    DataPart,
    DatasetManifest,
    DatasetSummary,
    data_url,
    encoded_sort_key,
    find_encoded_position,
    load_collection_manifest,
    load_figure_window,
)
from perimeter_app.figures import encode_row_masks


class CanonicalDataTests(unittest.TestCase):
    def setUp(self):
        self.part_rows = {
            "part-0.json": [[4, 5], [4, 7], [5, 5]],
            "part-1.json": [[5, 7], [6, 5], [6, 7]],
        }
        self.manifest = DatasetManifest(
            area=6,
            perimeter=14,
            order="canonical-v1",
            encoding="row-masks-v1",
            total=6,
            parts=(
                DataPart(
                    file="part-0.json",
                    count=3,
                    start=0,
                    bytes=10,
                    first_key=encoded_sort_key(self.part_rows["part-0.json"][0]),
                    last_key=encoded_sort_key(self.part_rows["part-0.json"][-1]),
                ),
                DataPart(
                    file="part-1.json",
                    count=3,
                    start=3,
                    bytes=10,
                    first_key=encoded_sort_key(self.part_rows["part-1.json"][0]),
                    last_key=encoded_sort_key(self.part_rows["part-1.json"][-1]),
                ),
            ),
        )

    def load_part(self, filename):
        return self.part_rows[filename]

    def test_data_url_uses_canonical_collection(self):
        self.assertEqual(
            data_url("manifest-4-8.json"),
            "https://wgarym.github.io/polyomino-canonical-data/manifest-4-8.json",
        )

    @patch("perimeter_app.canonical_data.fetch_json_document")
    def test_collection_exposes_available_perimeters(self, fetch_document):
        fetch_document.return_value = {
            "order": "canonical-v1",
            "encoding": "row-masks-v1",
            "datasets": [
                {"area": 4, "perimeter": 8, "total": 1, "manifest": "a.json"},
                {"area": 4, "perimeter": 10, "total": 4, "manifest": "b.json"},
            ],
        }
        collection = load_collection_manifest()
        self.assertEqual(collection.perimeters(4), (8, 10))

    def test_forward_window_crosses_a_part_boundary(self):
        figures = load_figure_window(
            self.manifest,
            displayed_start=2,
            reverse_order=False,
            count=3,
            load_part=self.load_part,
        )
        self.assertEqual(
            [encode_row_masks(figure) for figure in figures],
            [[5, 5], [5, 7], [6, 5]],
        )

    def test_reverse_window_crosses_a_part_boundary(self):
        figures = load_figure_window(
            self.manifest,
            displayed_start=1,
            reverse_order=True,
            count=3,
            load_part=self.load_part,
        )
        self.assertEqual(
            [encode_row_masks(figure) for figure in figures],
            [[6, 5], [5, 7], [5, 5]],
        )

    def test_search_returns_global_position(self):
        self.assertEqual(
            find_encoded_position(self.manifest, [5, 7], self.load_part),
            3,
        )
        self.assertEqual(
            find_encoded_position(self.manifest, [7, 7], self.load_part),
            -1,
        )


if __name__ == "__main__":
    unittest.main()
