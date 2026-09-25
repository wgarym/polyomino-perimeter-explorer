"""Validate every manifest, segment, and encoded figure in a collection."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path

from tools.build_datasets import ENCODING_VERSION, ORDER_VERSION


class CollectionValidationError(RuntimeError):
    pass


def row_mask_key(row_masks: list[int]) -> tuple:
    width = max(mask.bit_length() for mask in row_masks)
    return -width, len(row_masks), tuple(row_masks)


def row_mask_perimeter(row_masks: list[int]) -> int:
    area = sum(mask.bit_count() for mask in row_masks)
    horizontal_adjacencies = sum((mask & (mask >> 1)).bit_count() for mask in row_masks)
    vertical_adjacencies = sum(
        (upper & lower).bit_count()
        for upper, lower in zip(row_masks, row_masks[1:])
    )
    return 4 * area - 2 * (horizontal_adjacencies + vertical_adjacencies)


def _fail(message: str) -> None:
    raise CollectionValidationError(message)


def validate_collection(data_directory: Path) -> dict[str, object]:
    collection_path = data_directory / "collection-manifest.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    if collection.get("order") != ORDER_VERSION:
        _fail("Unexpected collection ordering version.")
    if collection.get("encoding") != ENCODING_VERSION:
        _fail("Unexpected collection encoding version.")

    total_cases = 0
    total_bytes = 0
    total_parts = 0
    largest_part = 0
    for dataset_entry in collection["datasets"]:
        manifest_path = data_directory / dataset_entry["manifest"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        area = manifest["area"]
        perimeter = manifest["perimeter"]
        if (area, perimeter) != (
            dataset_entry["area"],
            dataset_entry["perimeter"],
        ):
            _fail(f"Dataset identity mismatch in {manifest_path.name}.")

        dataset_count = 0
        dataset_bytes = 0
        previous_key = None
        for part in manifest["parts"]:
            part_path = data_directory / part["file"]
            payload = part_path.read_bytes()
            if len(payload) != part["bytes"]:
                _fail(f"Byte count mismatch in {part_path.name}.")
            if len(payload) > collection["target_bytes"]:
                _fail(f"Segment exceeds target size: {part_path.name}.")
            if hashlib.sha256(payload).hexdigest() != part["sha256"]:
                _fail(f"Checksum mismatch in {part_path.name}.")
            if part["start"] != dataset_count:
                _fail(f"Cumulative offset mismatch in {part_path.name}.")

            figures = json.loads(payload)
            if len(figures) != part["count"]:
                _fail(f"Case count mismatch in {part_path.name}.")
            if not figures:
                _fail(f"Empty segment: {part_path.name}.")

            for row_masks in figures:
                if not row_masks or any(mask <= 0 for mask in row_masks):
                    _fail(f"Invalid row masks in {part_path.name}.")
                key = row_mask_key(row_masks)
                if previous_key is not None and key <= previous_key:
                    _fail(f"Non-unique or unordered figure in {part_path.name}.")
                if sum(mask.bit_count() for mask in row_masks) != area:
                    _fail(f"Area mismatch in {part_path.name}.")
                if row_mask_perimeter(row_masks) != perimeter:
                    _fail(f"Perimeter mismatch in {part_path.name}.")
                previous_key = key

            first_key = {
                "width": -row_mask_key(figures[0])[0],
                "height": len(figures[0]),
                "rows": figures[0],
            }
            last_key = {
                "width": -row_mask_key(figures[-1])[0],
                "height": len(figures[-1]),
                "rows": figures[-1],
            }
            if first_key != part["first_key"] or last_key != part["last_key"]:
                _fail(f"Key range mismatch in {part_path.name}.")

            dataset_count += len(figures)
            dataset_bytes += len(payload)
            total_parts += 1
            largest_part = max(largest_part, len(payload))

        if dataset_count != manifest["total"] or dataset_count != dataset_entry["total"]:
            _fail(f"Dataset total mismatch for area {area}, perimeter {perimeter}.")
        if dataset_bytes != dataset_entry["bytes"]:
            _fail(f"Dataset byte mismatch for area {area}, perimeter {perimeter}.")
        total_cases += dataset_count
        total_bytes += dataset_bytes

    if total_cases != collection["total_cases"]:
        _fail("Collection case total mismatch.")
    if total_bytes != collection["total_bytes"]:
        _fail("Collection byte total mismatch.")
    if len(collection["datasets"]) != collection["dataset_count"]:
        _fail("Collection dataset total mismatch.")

    return {
        "valid": True,
        "order": collection["order"],
        "encoding": collection["encoding"],
        "datasets": collection["dataset_count"],
        "parts": total_parts,
        "cases": total_cases,
        "bytes": total_bytes,
        "largest_part_bytes": largest_part,
    }


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_directory", type=Path)
    return parser.parse_args(arguments)


def main() -> None:
    arguments = parse_arguments()
    report = validate_collection(arguments.data_directory)
    report_path = arguments.data_directory / "validation-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
