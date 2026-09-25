"""Incremental access to the canonical GitHub Pages dataset collection."""

from bisect import bisect_right
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import json
from typing import Any

import requests

from .config import CANONICAL_DATA_BASE_URL
from .data import DatasetError
from .figures import Matrix, RowMasks, decode_row_masks


EXPECTED_ORDER = "canonical-v1"
EXPECTED_ENCODING = "row-masks-v1"


@dataclass(frozen=True)
class DatasetSummary:
    area: int
    perimeter: int
    total: int
    manifest: str


@dataclass(frozen=True)
class CollectionManifest:
    order: str
    encoding: str
    datasets: tuple[DatasetSummary, ...]

    def perimeters(self, area: int) -> tuple[int, ...]:
        return tuple(
            item.perimeter for item in self.datasets if item.area == area
        )


@dataclass(frozen=True)
class DataPart:
    file: str
    count: int
    start: int
    bytes: int
    first_key: tuple[int, int, tuple[int, ...]]
    last_key: tuple[int, int, tuple[int, ...]]

    @property
    def stop(self) -> int:
        return self.start + self.count


@dataclass(frozen=True)
class DatasetManifest:
    area: int
    perimeter: int
    order: str
    encoding: str
    total: int
    parts: tuple[DataPart, ...]


PartLoader = Callable[[str], list[RowMasks]]


def data_url(filename: str) -> str:
    return f"{CANONICAL_DATA_BASE_URL}/{filename}"


def fetch_json_document(url: str) -> Any:
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            raise DatasetError("The selected canonical dataset has not been published yet.")
        response.raise_for_status()
        return response.json()
    except DatasetError:
        raise
    except (requests.RequestException, json.JSONDecodeError) as exc:
        raise DatasetError(f"Could not load {url}: {exc}") from exc


def _require_mapping(payload: Any, url: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DatasetError(f"The manifest at {url} is not a JSON object.")
    return payload


def _validate_format(order: Any, encoding: Any, url: str) -> None:
    if order != EXPECTED_ORDER or encoding != EXPECTED_ENCODING:
        raise DatasetError(
            f"The manifest at {url} uses an unsupported order or encoding."
        )


def load_collection_manifest() -> CollectionManifest:
    url = data_url("collection-manifest.json")
    payload = _require_mapping(fetch_json_document(url), url)
    _validate_format(payload.get("order"), payload.get("encoding"), url)

    try:
        datasets = tuple(
            DatasetSummary(
                area=int(item["area"]),
                perimeter=int(item["perimeter"]),
                total=int(item["total"]),
                manifest=str(item["manifest"]),
            )
            for item in payload["datasets"]
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DatasetError(f"The collection manifest at {url} is malformed.") from exc

    return CollectionManifest(
        order=EXPECTED_ORDER,
        encoding=EXPECTED_ENCODING,
        datasets=datasets,
    )


def _manifest_key(value: Any) -> tuple[int, int, tuple[int, ...]]:
    try:
        width = int(value["width"])
        height = int(value["height"])
        rows = tuple(int(row) for row in value["rows"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DatasetError("A canonical dataset key is malformed.") from exc
    return -width, height, rows


def load_dataset_manifest(area: int, perimeter: int) -> DatasetManifest:
    filename = f"manifest-{area}-{perimeter}.json"
    url = data_url(filename)
    payload = _require_mapping(fetch_json_document(url), url)
    _validate_format(payload.get("order"), payload.get("encoding"), url)

    try:
        parts = tuple(
            DataPart(
                file=str(item["file"]),
                count=int(item["count"]),
                start=int(item["start"]),
                bytes=int(item["bytes"]),
                first_key=_manifest_key(item["first_key"]),
                last_key=_manifest_key(item["last_key"]),
            )
            for item in payload["parts"]
        )
        manifest = DatasetManifest(
            area=int(payload["area"]),
            perimeter=int(payload["perimeter"]),
            order=EXPECTED_ORDER,
            encoding=EXPECTED_ENCODING,
            total=int(payload["total"]),
            parts=parts,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise DatasetError(f"The dataset manifest at {url} is malformed.") from exc

    if manifest.area != area or manifest.perimeter != perimeter:
        raise DatasetError(f"The dataset manifest at {url} identifies another dataset.")
    if not manifest.parts or manifest.parts[0].start != 0:
        raise DatasetError(f"The dataset manifest at {url} has invalid part offsets.")
    expected_start = 0
    for part in manifest.parts:
        if part.start != expected_start or part.count <= 0:
            raise DatasetError(f"The dataset manifest at {url} has invalid part offsets.")
        expected_start = part.stop
    if expected_start != manifest.total:
        raise DatasetError(f"The dataset manifest at {url} has an invalid total.")
    return manifest


def load_data_part(filename: str) -> list[RowMasks]:
    url = data_url(filename)
    payload = fetch_json_document(url)
    if not isinstance(payload, list):
        raise DatasetError(f"The data part at {url} is not a JSON list.")
    return payload


def encoded_sort_key(row_masks: Sequence[int]) -> tuple[int, int, tuple[int, ...]]:
    if not row_masks:
        raise DatasetError("A canonical figure has no rows.")
    rows = tuple(int(row) for row in row_masks)
    width = max(row.bit_length() for row in rows)
    return -width, len(rows), rows


def _part_index_for_position(manifest: DatasetManifest, position: int) -> int:
    if not 0 <= position < manifest.total:
        raise DatasetError("The requested position is outside the dataset.")
    starts = tuple(part.start for part in manifest.parts)
    return bisect_right(starts, position) - 1


def load_figure_window(
    manifest: DatasetManifest,
    displayed_start: int,
    reverse_order: bool,
    count: int,
    load_part: PartLoader,
) -> list[Matrix]:
    """Load at most ``count`` figures beginning at a displayed position."""
    if manifest.total <= 0 or count <= 0:
        return []

    displayed_start = max(0, min(displayed_start, manifest.total - 1))
    canonical_position = (
        manifest.total - displayed_start - 1
        if reverse_order
        else displayed_start
    )
    figures: list[Matrix] = []

    while len(figures) < count and 0 <= canonical_position < manifest.total:
        part_index = _part_index_for_position(manifest, canonical_position)
        part = manifest.parts[part_index]
        encoded = load_part(part.file)
        if len(encoded) != part.count:
            raise DatasetError(
                f"The data part {part.file} contains {len(encoded):,} figures; "
                f"its manifest declares {part.count:,}."
            )

        local_position = canonical_position - part.start
        needed = count - len(figures)
        if reverse_order:
            take = min(needed, local_position + 1)
            selected = reversed(encoded[local_position - take + 1 : local_position + 1])
            canonical_position -= take
        else:
            take = min(needed, part.count - local_position)
            selected = encoded[local_position : local_position + take]
            canonical_position += take

        figures.extend(decode_row_masks(row_masks) for row_masks in selected)
    return figures


def _part_index_for_key(
    manifest: DatasetManifest,
    target_key: tuple[int, int, tuple[int, ...]],
) -> int:
    low = 0
    high = len(manifest.parts)
    while low < high:
        middle = (low + high) // 2
        if manifest.parts[middle].last_key < target_key:
            low = middle + 1
        else:
            high = middle
    if low == len(manifest.parts):
        return -1
    part = manifest.parts[low]
    return low if part.first_key <= target_key <= part.last_key else -1


def find_encoded_position(
    manifest: DatasetManifest,
    row_masks: Sequence[int],
    load_part: PartLoader,
) -> int:
    """Return the canonical zero-based position of an encoded figure."""
    target_key = encoded_sort_key(row_masks)
    part_index = _part_index_for_key(manifest, target_key)
    if part_index < 0:
        return -1

    part = manifest.parts[part_index]
    encoded = load_part(part.file)
    if len(encoded) != part.count:
        raise DatasetError(
            f"The data part {part.file} does not match its manifest count."
        )

    low = 0
    high = len(encoded)
    while low < high:
        middle = (low + high) // 2
        if encoded_sort_key(encoded[middle]) < target_key:
            low = middle + 1
        else:
            high = middle
    if low < len(encoded) and encoded_sort_key(encoded[low]) == target_key:
        return part.start + low
    return -1
