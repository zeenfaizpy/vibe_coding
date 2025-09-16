"""Download selected IMDB datasets from https://datasets.imdbws.com/.

This script fetches the gzip-compressed TSV files provided by IMDB and saves
them in the specified output directory.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

BASE_URL = "https://datasets.imdbws.com/"
DEFAULT_FILES = [
    "name.basics.tsv.gz",
    "title.basics.tsv.gz",
    "title.principals.tsv.gz",
    "title.ratings.tsv.gz",
]


def download_file(file_name: str, output_dir: Path, overwrite: bool = False) -> Path:
    """Download a single file from IMDB.

    Args:
        file_name: Filename available at BASE_URL.
        output_dir: Directory to store the downloaded file.
        overwrite: Whether to overwrite an existing local copy.

    Returns:
        Path to the downloaded file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / file_name

    if destination.exists() and not overwrite:
        print(f"Skipping {file_name}; file already exists at {destination}.")
        return destination

    url = f"{BASE_URL}{file_name}"
    print(f"Downloading {url} -> {destination}")

    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(destination, "wb") as file_obj:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:  # filter out keep-alive chunks
                    file_obj.write(chunk)

    print(f"Finished downloading {file_name}")
    return destination


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory where downloaded files will be stored.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=DEFAULT_FILES,
        help=(
            "Specific file names to download. Defaults to a curated subset of "
            "the IMDB datasets."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download files even if they already exist locally.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    for file_name in args.files:
        try:
            download_file(file_name, args.output_dir, overwrite=args.overwrite)
        except requests.HTTPError as exc:  # pragma: no cover - network errors are runtime issues
            print(f"Failed to download {file_name}: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
