"""Pure polyomino parsing, measurement, and symmetry operations."""

from collections import deque
from collections.abc import Iterable, Sequence

Matrix = list[list[int]]


def copy_matrix(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(row) for row in matrix]


def reflect_vertical(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(row) for row in reversed(matrix)]


def reflect_horizontal(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(reversed(row)) for row in matrix]


def reflect_diagonal(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(row) for row in zip(*matrix)]


def reflect_antidiagonal(matrix: Sequence[Sequence[int]]) -> Matrix:
    return rotate_clockwise(rotate_clockwise(reflect_diagonal(matrix)))


def rotate_clockwise(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(reversed(column)) for column in zip(*matrix)]


def rotate_half(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(reversed(row)) for row in reversed(matrix)]


def rotate_counterclockwise(matrix: Sequence[Sequence[int]]) -> Matrix:
    return [list(column) for column in reversed(list(zip(*matrix)))]


def trim_figure(matrix: Sequence[Sequence[int]]) -> Matrix:
    if not matrix or not matrix[0]:
        return []

    copied = copy_matrix(matrix)
    filled = [
        (row_index, column_index)
        for row_index, row in enumerate(copied)
        for column_index, value in enumerate(row)
        if value
    ]
    if not filled:
        return []

    top = min(point[0] for point in filled)
    bottom = max(point[0] for point in filled)
    left = min(point[1] for point in filled)
    right = max(point[1] for point in filled)
    return [row[left : right + 1] for row in copied[top : bottom + 1]]


def normalize_figure(matrix: Sequence[Sequence[int]]) -> Matrix:
    figure = trim_figure(matrix)
    if not figure:
        return []

    if len(figure) < len(figure[0]):
        figure = rotate_clockwise(figure)

    midpoint = len(figure) // 2
    top_sum = sum(sum(row) for row in figure[:midpoint])
    lower_start = midpoint + len(figure) % 2
    bottom_sum = sum(sum(row) for row in figure[lower_start:])
    if top_sum > bottom_sum:
        figure = reflect_vertical(figure)

    midpoint = len(figure[0]) // 2
    left_sum = sum(sum(row[:midpoint]) for row in figure)
    right_start = midpoint + len(figure[0]) % 2
    right_sum = sum(sum(row[right_start:]) for row in figure)
    if right_sum > left_sum:
        figure = reflect_horizontal(figure)
    return figure


def area(matrix: Sequence[Sequence[int]]) -> int:
    return sum(sum(row) for row in matrix)


def perimeter(matrix: Sequence[Sequence[int]]) -> int:
    if not matrix or not matrix[0]:
        return 0

    height = len(matrix)
    width = len(matrix[0])
    exposed = 0
    for row in range(height):
        for column in range(width):
            if not matrix[row][column]:
                continue
            for delta_row, delta_column in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                neighbor_row = row + delta_row
                neighbor_column = column + delta_column
                if not (0 <= neighbor_row < height and 0 <= neighbor_column < width):
                    exposed += 1
                elif not matrix[neighbor_row][neighbor_column]:
                    exposed += 1
    return exposed


def is_connected(matrix: Sequence[Sequence[int]]) -> bool:
    figure = trim_figure(matrix)
    if not figure:
        return False

    filled = {
        (row_index, column_index)
        for row_index, row in enumerate(figure)
        for column_index, value in enumerate(row)
        if value
    }
    start = next(iter(filled))
    visited = {start}
    queue = deque([start])
    while queue:
        row, column = queue.popleft()
        for delta_row, delta_column in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            neighbor = row + delta_row, column + delta_column
            if neighbor in filled and neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return visited == filled


def parse_figure(value: str) -> Matrix:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    row_strings = normalized.replace("\n", ",").split(",")
    rows = []
    for row_string in row_strings:
        if not row_string and not rows:
            continue
        rows.append([1 if character in "#Xx1" else 0 for character in row_string])

    if not rows or not any(rows):
        return []
    row_width = max(len(row) for row in rows)
    return trim_figure([row + [0] * (row_width - len(row)) for row in rows])


def symmetries(matrix: Sequence[Sequence[int]]) -> Iterable[Matrix]:
    operations = (
        copy_matrix,
        reflect_vertical,
        reflect_horizontal,
        reflect_diagonal,
        reflect_antidiagonal,
        rotate_clockwise,
        rotate_half,
        rotate_counterclockwise,
    )
    seen = set()
    for operation in operations:
        image = operation(matrix)
        marker = tuple(tuple(row) for row in image)
        if marker not in seen:
            seen.add(marker)
            yield image


def find_figure(needle: Sequence[Sequence[int]], figures: Sequence[Matrix]) -> int:
    positions = {
        tuple(tuple(row) for row in figure): index
        for index, figure in enumerate(figures)
    }
    for image in symmetries(needle):
        marker = tuple(tuple(row) for row in image)
        if marker in positions:
            return positions[marker]
    return -1

