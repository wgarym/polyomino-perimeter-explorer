import unittest

from perimeter_app.figures import (
    area,
    canonical_figure,
    canonical_sort_key,
    decode_row_masks,
    encode_row_masks,
    find_figure,
    is_connected,
    normalize_figure,
    parse_figure,
    perimeter,
    rotate_clockwise,
    symmetries,
    trim_figure,
)


class FigureTests(unittest.TestCase):
    def test_parse_and_trim(self):
        self.assertEqual(parse_figure("..#.,.##."), [[0, 1], [1, 1]])
        self.assertEqual(parse_figure("..#.\n.##."), [[0, 1], [1, 1]])
        self.assertEqual(trim_figure([[0, 0], [0, 1]]), [[1]])

    def test_area_and_perimeter(self):
        square = [[1, 1], [1, 1]]
        self.assertEqual(area(square), 4)
        self.assertEqual(perimeter(square), 8)

    def test_connectivity(self):
        self.assertTrue(is_connected([[1, 1], [0, 1]]))
        self.assertFalse(is_connected([[1, 0], [0, 1]]))

    def test_search_accepts_rotation(self):
        figure = [[1, 0], [1, 1]]
        rotated = rotate_clockwise(figure)
        self.assertEqual(find_figure(rotated, [normalize_figure(figure)]), 0)

    def test_canonical_figure_is_identical_for_every_symmetry(self):
        figure = [[0, 1], [1, 1], [1, 0]]
        canonical_variants = {
            tuple(tuple(row) for row in canonical_figure(image))
            for image in symmetries(figure)
        }
        self.assertEqual(len(canonical_variants), 1)

    def test_canonical_sort_key_uses_dimensions_then_bitmap(self):
        first = canonical_figure([[1, 1], [1, 0]])
        second = canonical_figure([[1], [1], [1]])
        self.assertLess(canonical_sort_key(first), canonical_sort_key(second))

    def test_row_mask_encoding_round_trips_canonical_figure(self):
        figure = canonical_figure([[0, 1], [1, 1], [1, 0]])
        self.assertEqual(decode_row_masks(encode_row_masks(figure)), figure)


if __name__ == "__main__":
    unittest.main()
