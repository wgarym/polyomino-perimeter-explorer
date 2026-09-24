import unittest

from perimeter_app.display import pack_page, recommended_screen_width, render_page


class DisplayTests(unittest.TestCase):
    def test_recommended_width_uses_content_width_and_block_size(self):
        self.assertEqual(recommended_screen_width(630, 14), 45)
        self.assertEqual(recommended_screen_width(350, 14), 25)
        self.assertEqual(recommended_screen_width(2000, 14), 100)

    def test_page_always_contains_at_least_one_figure(self):
        figures = [[[1] * 20]]
        page = pack_page(figures, 0, screen_width=5, screen_height=5)
        self.assertEqual((page.start, page.end), (0, 1))

    def test_page_respects_width(self):
        figures = [[[1]], [[1]], [[1]]]
        page = pack_page(figures, 0, screen_width=7, screen_height=20)
        self.assertEqual(page.end, 3)
        self.assertEqual(len(page.rows), 3)

    def test_render_includes_solution_numbers(self):
        page = pack_page([[[1]], [[1, 1]]], 0, 20, 20)
        html = render_page(page)
        self.assertIn("No. 1", html)
        self.assertIn("No. 2", html)
        self.assertIn("cols-2", html)


if __name__ == "__main__":
    unittest.main()
