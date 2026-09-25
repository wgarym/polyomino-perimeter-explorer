"""Pure polyomino parsing, measurement, and symmetry operations."""

from collections import deque
from collections.abc import Iterable, Sequence

Matrix = list[list[int]]
RowMasks = list[int]


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


def _outer_mass_profile(values: Sequence[int]) -> tuple[int, ...]:
    """Compare a half, then progressively remove positions near the center."""
    half = len(values) // 2
    return tuple(sum(values[:count]) for count in range(half, 0, -1))


def canonical_orientation_rank(matrix: Sequence[Sequence[int]]) -> tuple:
    """Rank portrait orientations by left weight, bottom weight, then cells."""
    column_totals = tuple(
        sum(row[column] for row in matrix)
        for column in range(len(matrix[0]))
    )
    row_totals = tuple(sum(row) for row in matrix)
    left_profile = _outer_mass_profile(column_totals)
    bottom_profile = _outer_mass_profile(tuple(reversed(row_totals)))
    bottom_left_bitmap = tuple(
        cell
        for row in reversed(matrix)
        for cell in row
    )
    return left_profile, bottom_profile, bottom_left_bitmap


def canonical_figure(matrix: Sequence[Sequence[int]]) -> Matrix:
    """Return one deterministic representative of a figure's symmetries."""
    figure = trim_figure(matrix)
    if not figure:
        return []

    candidates = [trim_figure(image) for image in symmetries(figure)]
    portrait_candidates = [
        candidate
        for candidate in candidates
        if len(candidate) >= len(candidate[0])
    ]
    return copy_matrix(max(portrait_candidates, key=canonical_orientation_rank))


def canonical_sort_key(matrix: Sequence[Sequence[int]]) -> tuple:
    """Return the stable wide-first display key for a canonical figure."""
    width = len(matrix[0])
    height = len(matrix)
    bitmap = tuple(cell for row in matrix for cell in row)
    return -width, height, bitmap


def encode_row_masks(matrix: Sequence[Sequence[int]]) -> RowMasks:
    """Encode a trimmed matrix as one integer bit mask per row."""
    figure = trim_figure(matrix)
    if not figure:
        return []
    width = len(figure[0])
    return [
        sum(cell << (width - column - 1) for column, cell in enumerate(row))
        for row in figure
    ]


def decode_row_masks(row_masks: Sequence[int]) -> Matrix:
    """Decode row masks whose highest used bit defines the figure width."""
    if not row_masks or not any(row_masks):
        return []
    width = max(mask.bit_length() for mask in row_masks)
    return [
        [(mask >> (width - column - 1)) & 1 for column in range(width)]
        for mask in row_masks
    ]


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
