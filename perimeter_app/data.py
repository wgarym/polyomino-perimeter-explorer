"""Loading and validation for the GitHub-hosted JSON datasets."""

import json

import requests

from .config import DATA_BASE_URL, MAX_FILE_INDEX, dataset_last_part
from .figures import Matrix, normalize_figure


class DatasetError(RuntimeError):
    pass


def dataset_url(area: int, perimeter: int, part: int) -> str:
    return f"{DATA_BASE_URL}/data-{area}-{perimeter}-{part}.json"


def fetch_json(url: str) -> list[Matrix]:
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            raise DatasetError("The selected dataset has not been published yet.")
        response.raise_for_status()
        payload = response.json()
    except DatasetError:
        raise
    except (requests.RequestException, json.JSONDecodeError) as exc:
        raise DatasetError(f"Could not load {url}: {exc}") from exc

    if not isinstance(payload, list):
        raise DatasetError(f"The dataset at {url} is not a JSON list.")
    return payload


def load_dataset(area: int, perimeter: int) -> list[Matrix]:
    try:
        last_part = dataset_last_part(area, perimeter)
    except ValueError as exc:
        raise DatasetError(str(exc)) from exc

    if last_part > MAX_FILE_INDEX:
        raise DatasetError(
            "This dataset is too large for the prototype. "
            "Choose a smaller perimeter."
        )

    figures = []
    for part in range(last_part + 1):
        figures.extend(fetch_json(dataset_url(area, perimeter, part)))

    normalized = [normalize_figure(figure) for figure in figures]
    normalized = [figure for figure in normalized if figure]
    normalized.sort(key=lambda figure: (-len(figure[0]), len(figure)))
    return normalized
