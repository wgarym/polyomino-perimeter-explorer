import unittest

from perimeter_app.figures import (
    area,
    find_figure,
    is_connected,
    normalize_figure,
    parse_figure,
    perimeter,
    rotate_clockwise,
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


if __name__ == "__main__":
    unittest.main()
