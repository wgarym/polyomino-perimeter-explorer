"""Dataset limits and valid area/perimeter combinations."""

DATA_BASE_URL = "https://wgarym.github.io/perimeter"
CANONICAL_DATA_BASE_URL = "https://wgarym.github.io/polyomino-canonical-data"
MIN_AREA = 4
MAX_AREA = 16
MAX_FILE_INDEX = 53

# Indexes correspond to area. Entries beyond MAX_AREA are retained from the
# original notebook so future data can be enabled without changing the table.
MIN_PERIMETERS = (
    3,
    4,
    6,
    8,
    8,
    10,
    10,
    12,
    12,
    12,
    14,
    14,
    14,
    16,
    16,
    16,
    16,
    18,
    18,
    18,
)

# Each value is the final numbered JSON part, so 0 means one file (part 0).
DATASET_LAST_PART = (
    (0,),
    (0,),
    (0,),
    (0,),
    (0, 0),
    (0, 0),
    (0, 0, 0),
    (0, 0, 0),
    (0, 0, 0, 0),
    (0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 0),
    (0, 0, 0, 0, 0, 2, 3),
    (0, 0, 0, 0, 0, 3, 9, 13),
    (0, 0, 0, 0, 1, 4, 17, 40, 53),
    (0, 0, 0, 0, 1, 5, 24, 78, 168, 208),
)


def perimeter_bounds(area: int) -> tuple[int, int]:
    if not MIN_AREA <= area <= MAX_AREA:
        raise ValueError(f"Area must be between {MIN_AREA} and {MAX_AREA}.")
    return MIN_PERIMETERS[area], 2 * area + 2


def valid_perimeters(area: int) -> tuple[int, ...]:
    lower, upper = perimeter_bounds(area)
    return tuple(range(lower, upper + 1, 2))


def normalize_perimeter(value: int, area: int) -> int:
    options = valid_perimeters(area)
    return min(options, key=lambda option: (abs(option - value), option))


def perimeter_level(area: int, perimeter: int) -> int:
    lower, upper = perimeter_bounds(area)
    if perimeter < lower or perimeter > upper or (perimeter - lower) % 2:
        raise ValueError("Invalid area/perimeter combination.")
    return (perimeter - lower) // 2


def dataset_last_part(area: int, perimeter: int) -> int:
    level = perimeter_level(area, perimeter)
    if level >= len(DATASET_LAST_PART[area]):
        raise ValueError("No dataset is available for this combination.")
    return DATASET_LAST_PART[area][level]
