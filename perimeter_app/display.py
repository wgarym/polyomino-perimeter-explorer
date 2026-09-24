"""Page packing and browser rendering for polyomino figures."""

from dataclasses import dataclass
from html import escape
from typing import Sequence

from .figures import Matrix


@dataclass(frozen=True)
class FigurePage:
    rows: tuple[tuple[Matrix, ...], ...]
    start: int
    end: int


def recommended_screen_width(content_width: int, block_size: int) -> int:
    if content_width <= 0 or block_size <= 0:
        return 45
    fitted_width = round(content_width / block_size)
    return max(20, min(100, fitted_width))


def pack_page(
    figures: Sequence[Matrix],
    start: int,
    screen_width: int,
    screen_height: int,
) -> FigurePage:
    if not figures:
        return FigurePage((), 0, 0)

    index = max(0, min(start, len(figures) - 1))
    actual_start = index
    rows = []
    used_height = 0

    while index < len(figures):
        row = []
        row_width = 2
        row_height = 0

        while index < len(figures):
            figure = figures[index]
            figure_width = len(figure[0]) + 2
            if row and row_width + figure_width >= screen_width:
                break
            row.append(figure)
            row_width += figure_width
            row_height = max(row_height, len(figure))
            index += 1
            if row_width >= screen_width:
                break

        proposed_height = used_height + row_height + 2
        if rows and proposed_height >= screen_height:
            index -= len(row)
            break

        rows.append(tuple(row))
        used_height = proposed_height
        if proposed_height >= screen_height:
            break

    return FigurePage(tuple(rows), actual_start, index)


def render_page(page: FigurePage) -> str:
    rendered_rows = []
    figure_number = page.start + 1
    for row in page.rows:
        rendered_figures = []
        for figure in row:
            height = len(figure)
            width = len(figure[0])
            cells = "".join(
                f'<span class="poly-cell {"filled" if cell else "empty"}"></span>'
                for matrix_row in figure
                for cell in matrix_row
            )
            rendered_figures.append(
                '<figure class="poly-figure">'
                f'<div class="poly-grid cols-{width}" data-rows="{height}">{cells}</div>'
                f'<figcaption>{escape(f"No. {figure_number:,}")}</figcaption>'
                "</figure>"
            )
            figure_number += 1
        rendered_rows.append(
            '<div class="poly-row">' + "".join(rendered_figures) + "</div>"
        )
    return '<div class="poly-results">' + "".join(rendered_rows) + "</div>"
