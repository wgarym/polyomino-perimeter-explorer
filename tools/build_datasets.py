"""Canonicalize, externally sort, and segment an unsegmented dataset."""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
import resource
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator, Sequence
from pathlib import Path

from perimeter_app.figures import (
    Matrix,
    area as figure_area,
    canonical_figure,
    canonical_sort_key,
    encode_row_masks,
    perimeter as figure_perimeter,
)

ORDER_VERSION = "canonical-v1"
ENCODING_VERSION = "row-masks-v1"
DEFAULT_BATCH_SIZE = 50_000
SOURCE_PATTERN = re.compile(r"data-(\d+)-(\d+)\.json$")


class DatasetBuildError(RuntimeError):
    pass


def iter_json_array(path: Path, read_size: int = 1024 * 1024) -> Iterator[Matrix]:
    """Stream the values of a top-level JSON array using the standard library."""
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as source:
        buffer = ""
        position = 0
        started = False
        finished = False

        while not finished:
            if position >= len(buffer):
                buffer = source.read(read_size)
                position = 0
                if not buffer:
                    break

            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if not started:
                    if position >= len(buffer):
                        break
                    if buffer[position] != "[":
                        raise DatasetBuildError(f"{path} is not a JSON array.")
                    started = True
                    position += 1
                    continue
                while position < len(buffer) and (
                    buffer[position].isspace() or buffer[position] == ","
                ):
                    position += 1
                if position < len(buffer) and buffer[position] == "]":
                    finished = True
                break

            if finished:
                break
            if position >= len(buffer):
                continue

            while True:
                try:
                    value, end = decoder.raw_decode(buffer, position)
                    position = end
                    yield value
                    if position > read_size:
                        buffer = buffer[position:]
                        position = 0
                    break
                except json.JSONDecodeError as exc:
                    remainder = buffer[position:]
                    addition = source.read(read_size)
                    if not addition:
                        raise DatasetBuildError(
                            f"Invalid or incomplete JSON in {path}: {exc}"
                        ) from exc
                    buffer = remainder + addition
                    position = 0

        if not started or not finished:
            raise DatasetBuildError(f"Incomplete JSON array in {path}.")


def _write_run(records: list[Matrix], path: Path) -> None:
    records.sort(key=canonical_sort_key)
    with path.open("w", encoding="utf-8") as destination:
        for figure in records:
            destination.write(json.dumps(figure, separators=(",", ":")))
            destination.write("\n")


def _iter_run(path: Path) -> Iterator[tuple[tuple, Matrix]]:
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            figure = json.loads(line)
            yield canonical_sort_key(figure), figure


def build_sorted_spool(
    source_paths: Sequence[Path],
    spool_path: Path,
    area: int,
    perimeter: int,
    temporary_directory: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    """Canonicalize the source into one compact, sorted NDJSON spool."""
    run_paths = []
    batch = []
    source_count = 0

    for source_path in source_paths:
        for raw_figure in iter_json_array(source_path):
            figure = canonical_figure(raw_figure)
            if not figure:
                raise DatasetBuildError(
                    f"Empty figure at source position {source_count + 1}."
                )
            if figure_area(figure) != area or figure_perimeter(figure) != perimeter:
                raise DatasetBuildError(
                    f"Figure {source_count + 1} does not match area {area}, "
                    f"perimeter {perimeter}."
                )
            batch.append(figure)
            source_count += 1
            if len(batch) >= batch_size:
                run_path = temporary_directory / f"run-{len(run_paths):05d}.ndjson"
                _write_run(batch, run_path)
                run_paths.append(run_path)
                batch = []

    if batch:
        run_path = temporary_directory / f"run-{len(run_paths):05d}.ndjson"
        _write_run(batch, run_path)
        run_paths.append(run_path)

    if not run_paths:
        raise DatasetBuildError("No figures found in the source files.")

    merged = heapq.merge(*(_iter_run(path) for path in run_paths), key=lambda item: item[0])
    previous_key = None
    written_count = 0
    with spool_path.open("w", encoding="utf-8") as destination:
        for key, figure in merged:
            if key == previous_key:
                raise DatasetBuildError(
                    f"Duplicate canonical figure near sorted position {written_count + 1}."
                )
            destination.write(json.dumps(figure, separators=(",", ":")))
            destination.write("\n")
            previous_key = key
            written_count += 1

    if written_count != source_count:
        raise DatasetBuildError("The external sort changed the figure count.")
    return written_count


def _manifest_key(figure: Matrix) -> dict[str, object]:
    return {
        "width": len(figure[0]),
        "height": len(figure),
        "rows": encode_row_masks(figure),
    }


def segment_spool(
    spool_path: Path,
    output_directory: Path,
    area: int,
    perimeter: int,
    target_bytes: int,
) -> dict[str, object]:
    """Write a sorted spool as JSON-array parts bounded by target_bytes."""
    output_directory.mkdir(parents=True, exist_ok=True)
    for old_part in output_directory.glob(f"data-{area}-{perimeter}-*.json"):
        old_part.unlink()
    old_manifest = output_directory / f"manifest-{area}-{perimeter}.json"
    if old_manifest.exists():
        old_manifest.unlink()
    parts = []
    part_file = None
    part_path = None
    part_hash = None
    part_count = 0
    part_bytes = 0
    first_figure = None
    last_figure = None
    cumulative_count = 0

    def open_part() -> None:
        nonlocal part_file, part_path, part_hash, part_count, part_bytes
        nonlocal first_figure, last_figure
        part_path = output_directory / f"data-{area}-{perimeter}-{len(parts)}.json"
        part_file = part_path.open("wb")
        part_hash = hashlib.sha256()
        part_file.write(b"[")
        part_hash.update(b"[")
        part_count = 0
        part_bytes = 1
        first_figure = None
        last_figure = None

    def close_part() -> None:
        nonlocal part_file, cumulative_count
        if part_file is None:
            return
        part_file.write(b"]")
        part_hash.update(b"]")
        part_file.close()
        total_bytes = part_bytes + 1
        parts.append(
            {
                "file": part_path.name,
                "count": part_count,
                "start": cumulative_count,
                "bytes": total_bytes,
                "sha256": part_hash.hexdigest(),
                "first_key": _manifest_key(first_figure),
                "last_key": _manifest_key(last_figure),
            }
        )
        cumulative_count += part_count
        part_file = None

    open_part()
    with spool_path.open("rb") as source:
        for line in source:
            figure = json.loads(line)
            encoded = json.dumps(
                encode_row_masks(figure),
                separators=(",", ":"),
            ).encode()
            separator = b"," if part_count else b""
            if part_count and part_bytes + len(separator) + len(encoded) + 1 > target_bytes:
                close_part()
                open_part()
                separator = b""

            if first_figure is None:
                first_figure = figure
            last_figure = figure
            part_file.write(separator)
            part_file.write(encoded)
            part_hash.update(separator)
            part_hash.update(encoded)
            part_bytes += len(separator) + len(encoded)
            part_count += 1
    close_part()

    manifest = {
        "area": area,
        "perimeter": perimeter,
        "order": ORDER_VERSION,
        "encoding": ENCODING_VERSION,
        "total": cumulative_count,
        "target_bytes": target_bytes,
        "parts": parts,
    }
    manifest_path = output_directory / f"manifest-{area}-{perimeter}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_dataset(
    source_path: Path,
    output_root: Path,
    targets_mib: Sequence[int],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    match = SOURCE_PATTERN.fullmatch(source_path.name)
    if not match:
        raise DatasetBuildError("Source filename must be data-AREA-PERIMETER.json.")
    area, perimeter = (int(value) for value in match.groups())
    return build_dataset_sources(
        (source_path,),
        output_root,
        area,
        perimeter,
        targets_mib,
        batch_size,
    )


def build_dataset_sources(
    source_paths: Sequence[Path],
    output_root: Path,
    area: int,
    perimeter: int,
    targets_mib: Sequence[int],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    """Build one dataset from an unsegmented file or ordered source parts."""
    if not source_paths:
        raise DatasetBuildError("At least one source file is required.")
    started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="perimeter-build-") as temporary_name:
        temporary_directory = Path(temporary_name)
        spool_path = temporary_directory / "sorted.ndjson"
        total = build_sorted_spool(
            source_paths,
            spool_path,
            area,
            perimeter,
            temporary_directory,
            batch_size,
        )
        sort_seconds = time.perf_counter() - started
        variants = {}
        for target_mib in targets_mib:
            variant_started = time.perf_counter()
            output_directory = output_root / f"{target_mib}MiB"
            manifest = segment_spool(
                spool_path,
                output_directory,
                area,
                perimeter,
                target_mib * 1024 * 1024,
            )
            variants[str(target_mib)] = {
                "parts": len(manifest["parts"]),
                "seconds": time.perf_counter() - variant_started,
                "largest_part_bytes": max(part["bytes"] for part in manifest["parts"]),
            }

    peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_rss_mib = peak_rss / (1024 * 1024 if sys.platform == "darwin" else 1024)
    report = {
        "sources": [str(path) for path in source_paths],
        "area": area,
        "perimeter": perimeter,
        "total": total,
        "sort_seconds": sort_seconds,
        "peak_rss_mib": peak_rss_mib,
        "variants": variants,
        "total_seconds": time.perf_counter() - started,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / f"build-report-{area}-{perimeter}.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--targets-mib", type=int, nargs="+", default=(4, 8, 16))
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args(arguments)


def main() -> None:
    arguments = parse_arguments()
    report = build_dataset(
        arguments.source,
        arguments.output_root,
        arguments.targets_mib,
        arguments.batch_size,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
