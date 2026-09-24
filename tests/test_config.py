import unittest

from perimeter_app.config import (
    MIN_AREA,
    MAX_AREA,
    MAX_FILE_INDEX,
    dataset_last_part,
    normalize_perimeter,
    perimeter_bounds,
    valid_perimeters,
)


class ConfigTests(unittest.TestCase):
    def test_supported_area_minimum_is_four(self):
        self.assertEqual(MIN_AREA, 4)

    def test_every_area_has_expected_even_perimeter_options(self):
        for area in range(MIN_AREA, MAX_AREA + 1):
            lower, upper = perimeter_bounds(area)
            options = valid_perimeters(area)
            self.assertEqual(options[0], lower)
            self.assertEqual(options[-1], upper)
            self.assertTrue(all((value - lower) % 2 == 0 for value in options))

    def test_requested_examples(self):
        self.assertEqual(perimeter_bounds(4), (8, 10))
        self.assertEqual(perimeter_bounds(5), (10, 12))
        self.assertEqual(perimeter_bounds(16), (16, 34))

    def test_normalize_perimeter_clamps_and_uses_valid_step(self):
        self.assertEqual(normalize_perimeter(2, 5), 10)
        self.assertEqual(normalize_perimeter(11, 5), 10)
        self.assertEqual(normalize_perimeter(99, 5), 12)

    def test_dataset_part_mapping_matches_notebook(self):
        self.assertEqual(dataset_last_part(4, 8), 0)
        self.assertEqual(dataset_last_part(13, 28), 3)
        self.assertEqual(
            tuple(dataset_last_part(15, perimeter) for perimeter in range(16, 33, 2)),
            (0, 0, 0, 0, 1, 4, 17, 40, 53),
        )
        self.assertEqual(MAX_FILE_INDEX, 53)
        self.assertEqual(dataset_last_part(16, 28), 24)


if __name__ == "__main__":
    unittest.main()
