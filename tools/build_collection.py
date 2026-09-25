"""Build a resumable canonical collection from one or more source folders."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from tools.build_datasets import (
    DEFAULT_BATCH_SIZE,
    ENCODING_VERSION,
    ORDER_VERSION,
    build_dataset_sources,
)

FILE_PATTERN = re.compile(r"data-(\d+)-(\d+)(?:-(\d+))?\.json$")


def discover_sources(source_roots: Sequence[Path]) -> dict[tuple[int, int], tuple[Path, ...]]:
    """Prefer the first unsegmented source; otherwise use ordered parts."""
    unsegmented: dict[tuple[int, int], Path] = {}
    segmented: dict[tuple[int, int], dict[int, Path]] = defaultdict(dict)

    for root in source_roots:
        for path in sorted(root.glob("data-*.json")):
            match = FILE_PATTERN.fullmatch(path.name)
            if not match:
                continue
            area, perimeter = (int(value) for value in match.groups()[:2])
            part_text = match.group(3)
            key = area, perimeter
            if part_text is None:
                unsegmented.setdefault(key, path)
            elif key not in unsegmented:
                segmented[key].setdefault(int(part_text), path)

    discovered = {}
    for key in sorted(set(unsegmented) | set(segmented)):
        if key in unsegmented:
            discovered[key] = (unsegmented[key],)
            continue
        parts = segmented[key]
        expected = list(range(max(parts) + 1))
        if sorted(parts) != expected:
            raise ValueError(f"Missing source parts for area {key[0]}, perimeter {key[1]}.")
        discovered[key] = tuple(parts[index] for index in expected)
    return discovered


def manifest_is_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("order") != ORDER_VERSION:
            return False
        if manifest.get("encoding") != ENCODING_VERSION:
            return False
        count = 0
        for part in manifest["parts"]:
            part_path = path.parent / part["file"]
            if not part_path.exists() or part_path.stat().st_size != part["bytes"]:
                return False
            if hashlib.sha256(part_path.read_bytes()).hexdigest() != part["sha256"]:
                return False
            count += part["count"]
        return count == manifest["total"]
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _build_one(
    source_paths: tuple[Path, ...],
    output_root: Path,
    area: int,
    perimeter: int,
    target_mib: int,
    batch_size: int,
) -> dict[str, object]:
    return build_dataset_sources(
        source_paths,
        output_root,
        area,
        perimeter,
        (target_mib,),
        batch_size,
    )


def write_collection_manifest(output_root: Path, target_mib: int) -> dict[str, object]:
    data_directory = output_root / f"{target_mib}MiB"
    datasets = []
    total_cases = 0
    total_bytes = 0
    for path in sorted(data_directory.glob("manifest-*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        part_bytes = sum(part["bytes"] for part in manifest["parts"])
        datasets.append(
            {
                "area": manifest["area"],
                "perimeter": manifest["perimeter"],
                "total": manifest["total"],
                "bytes": part_bytes,
                "manifest": path.name,
            }
        )
        total_cases += manifest["total"]
        total_bytes += part_bytes
    datasets.sort(key=lambda item: (item["area"], item["perimeter"]))
    collection = {
        "order": ORDER_VERSION,
        "encoding": ENCODING_VERSION,
        "target_bytes": target_mib * 1024 * 1024,
        "dataset_count": len(datasets),
        "total_cases": total_cases,
        "total_bytes": total_bytes,
        "datasets": datasets,
    }
    (data_directory / "collection-manifest.json").write_text(
        json.dumps(collection, indent=2) + "\n",
        encoding="utf-8",
    )
    return collection


def build_collection(
    source_roots: Sequence[Path],
    output_root: Path,
    target_mib: int = 8,
    workers: int = 4,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, object]:
    sources = discover_sources(source_roots)
    data_directory = output_root / f"{target_mib}MiB"
    pending = []
    for (area, perimeter), source_paths in sources.items():
        manifest_path = data_directory / f"manifest-{area}-{perimeter}.json"
        if manifest_is_complete(manifest_path):
            print(f"resume: area={area} perimeter={perimeter}", flush=True)
        else:
            pending.append((area, perimeter, source_paths))

    completed = len(sources) - len(pending)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_tasks = {
            executor.submit(
                _build_one,
                source_paths,
                output_root,
                area,
                perimeter,
                target_mib,
                batch_size,
            ): (area, perimeter)
            for area, perimeter, source_paths in pending
        }
        for future in as_completed(future_tasks):
            area, perimeter = future_tasks[future]
            report = future.result()
            completed += 1
            print(
                f"complete {completed}/{len(sources)}: area={area} "
                f"perimeter={perimeter} cases={report['total']}",
                flush=True,
            )

    return write_collection_manifest(output_root, target_mib)


def parse_arguments(arguments: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("source_roots", type=Path, nargs="+")
    parser.add_argument("--target-mib", type=int, default=8)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser.parse_args(arguments)


def main() -> None:
    arguments = parse_arguments()
    collection = build_collection(
        arguments.source_roots,
        arguments.output_root,
        arguments.target_mib,
        arguments.workers,
        arguments.batch_size,
    )
    print(json.dumps(collection, indent=2), flush=True)


if __name__ == "__main__":
    main()
