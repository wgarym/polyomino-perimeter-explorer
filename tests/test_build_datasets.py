import json
import tempfile
import unittest
from pathlib import Path

from tools.build_collection import (
    discover_sources,
    manifest_is_complete,
    write_collection_manifest,
)
from tools.build_datasets import build_dataset, iter_json_array
from tools.validate_collection import validate_collection


class DatasetBuilderTests(unittest.TestCase):
    def test_streams_top_level_json_array(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "figures.json"
            figures = [[[1]], [[1, 1]], [[1], [1]]]
            path.write_text(json.dumps(figures, indent=4), encoding="utf-8")
            self.assertEqual(list(iter_json_array(path, read_size=7)), figures)

    def test_builds_sorted_size_bounded_parts_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data-4-10.json"
            figures = [
                [[1, 1, 1, 1]],
                [[1, 0], [1, 0], [1, 1]],
                [[1, 1, 1], [0, 1, 0]],
                [[0, 1, 1], [1, 1, 0]],
            ]
            source.write_text(json.dumps(figures, indent=4), encoding="utf-8")

            report = build_dataset(source, root / "output", (1,), batch_size=2)
            manifest_path = root / "output/1MiB/manifest-4-10.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(report["total"], 4)
            self.assertEqual(manifest["total"], 4)
            self.assertEqual(manifest["encoding"], "row-masks-v1")
            self.assertEqual(sum(part["count"] for part in manifest["parts"]), 4)
            self.assertTrue(all(part["bytes"] <= 1024 * 1024 for part in manifest["parts"]))

    def test_discovers_unsegmented_sources_before_parts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unsegmented = root / "data-4-10.json"
            unsegmented.write_text("[]", encoding="utf-8")
            (root / "data-4-10-0.json").write_text("[]", encoding="utf-8")
            (root / "data-5-12-0.json").write_text("[]", encoding="utf-8")
            (root / "data-5-12-1.json").write_text("[]", encoding="utf-8")

            sources = discover_sources((root,))

            self.assertEqual(sources[(4, 10)], (unsegmented,))
            self.assertEqual(
                [path.name for path in sources[(5, 12)]],
                ["data-5-12-0.json", "data-5-12-1.json"],
            )

    def test_generated_manifest_is_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data-4-10.json"
            figures = [
                [[1, 1, 1, 1]],
                [[1, 0], [1, 0], [1, 1]],
                [[1, 1, 1], [0, 1, 0]],
                [[0, 1, 1], [1, 1, 0]],
            ]
            source.write_text(json.dumps(figures), encoding="utf-8")
            build_dataset(source, root / "output", (1,), batch_size=2)
            manifest = root / "output/1MiB/manifest-4-10.json"
            self.assertTrue(manifest_is_complete(manifest))

            write_collection_manifest(root / "output", 1)
            validation = validate_collection(root / "output/1MiB")
            self.assertTrue(validation["valid"])
            self.assertEqual(validation["cases"], 4)


if __name__ == "__main__":
    unittest.main()
