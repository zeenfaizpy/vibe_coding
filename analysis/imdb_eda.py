"""Exploratory analysis of the IMDB datasets downloaded from datasets.imdbws.com.

The script focuses on the "title.basics" and "title.ratings" tables, which
capture core metadata about titles (movies, series, etc.) and user ratings.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

DEFAULT_CHUNK_SIZE = 250_000
DEFAULT_MIN_VOTES = 5_000
DEFAULT_TOP_N = 10
DEFAULT_MIN_GENRE_TITLES = 200


def load_ratings(path: Path, min_votes: int) -> pd.DataFrame:
    """Load the ratings table and filter by the minimum vote threshold."""
    if not path.exists():
        raise FileNotFoundError(f"Ratings file not found: {path}")

    ratings = pd.read_csv(
        path,
        sep="\t",
        compression="gzip",
        dtype={"tconst": "string", "averageRating": "float32", "numVotes": "int32"},
        na_values="\\N",
    )
    if min_votes:
        ratings = ratings.loc[ratings["numVotes"] >= min_votes].reset_index(drop=True)
    return ratings


def analyze_titles(
    basics_path: Path,
    ratings: pd.DataFrame | None = None,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    top_n: int = DEFAULT_TOP_N,
    min_genre_titles: int = DEFAULT_MIN_GENRE_TITLES,
) -> dict:
    """Iterate through the title.basics file and compute summary statistics."""
    if not basics_path.exists():
        raise FileNotFoundError(f"Title basics file not found: {basics_path}")

    type_counts: Counter[str] = Counter()
    genre_counts: Counter[str] = Counter()
    decade_counts: Counter[int] = Counter()
    adult_counts = {"adult": 0, "non_adult": 0}
    type_year_sum: defaultdict[str, float] = defaultdict(float)
    type_year_count: defaultdict[str, int] = defaultdict(int)
    rating_type_sum: defaultdict[str, float] = defaultdict(float)
    rating_type_count: defaultdict[str, int] = defaultdict(int)
    genre_rating_sum: defaultdict[str, float] = defaultdict(float)
    genre_rating_count: defaultdict[str, int] = defaultdict(int)

    total_titles = 0
    usecols = ["tconst", "titleType", "primaryTitle", "isAdult", "startYear", "genres"]

    iter_csv = pd.read_csv(
        basics_path,
        sep="\t",
        compression="gzip",
        usecols=usecols,
        dtype={"tconst": "string", "titleType": "category", "primaryTitle": "string"},
        na_values="\\N",
        chunksize=chunk_size,
    )

    ratings_lookup = None
    if ratings is not None:
        ratings_lookup = ratings.set_index("tconst")

    for chunk in iter_csv:
        total_titles += len(chunk)
        chunk["isAdult"] = pd.to_numeric(chunk["isAdult"], errors="coerce").fillna(0).astype("int8")
        chunk["startYear"] = pd.to_numeric(chunk["startYear"], errors="coerce")

        type_counts.update(chunk["titleType"].value_counts().to_dict())

        adult_counts["adult"] += int((chunk["isAdult"] == 1).sum())
        adult_counts["non_adult"] += int((chunk["isAdult"] == 0).sum())

        valid_years = chunk.dropna(subset=["startYear"])
        if not valid_years.empty:
            grouped_years = valid_years.groupby("titleType", observed=False)["startYear"].agg(["sum", "count"])  # type: ignore[arg-type]
            for title_type, row in grouped_years.iterrows():
                type_year_sum[title_type] += float(row["sum"])
                type_year_count[title_type] += int(row["count"])

            decades = (valid_years["startYear"] // 10 * 10).astype("int64")
            decade_counts.update(decades.value_counts().to_dict())

        genre_series = chunk["genres"].dropna()
        if not genre_series.empty:
            exploded_genres = genre_series.str.split(",").explode()
            genre_counts.update(exploded_genres)

        if ratings_lookup is not None:
            rated_chunk = chunk.merge(ratings_lookup, left_on="tconst", right_index=True, how="inner")
            if not rated_chunk.empty:
                type_rating = rated_chunk.groupby("titleType", observed=False)["averageRating"].agg(["sum", "count"])  # type: ignore[arg-type]
                for title_type, row in type_rating.iterrows():
                    rating_type_sum[title_type] += float(row["sum"])
                    rating_type_count[title_type] += int(row["count"])

                rated_genres = rated_chunk.dropna(subset=["genres"]).copy()
                if not rated_genres.empty:
                    rated_genres["genre"] = rated_genres["genres"].str.split(",")
                    rated_genres = rated_genres.explode("genre")
                    genre_rating = rated_genres.groupby("genre", observed=False)["averageRating"].agg(["sum", "count"])  # type: ignore[arg-type]
                    for genre, row in genre_rating.iterrows():
                        genre_rating_sum[genre] += float(row["sum"])
                        genre_rating_count[genre] += int(row["count"])

    average_start_year = {
        title_type: round(type_year_sum[title_type] / type_year_count[title_type], 1)
        for title_type in type_year_sum
        if type_year_count[title_type] > 0
    }

    ratings_by_type = []
    for title_type, count in sorted(rating_type_count.items(), key=lambda item: (-item[1], item[0])):
        average_rating = rating_type_sum[title_type] / count if count else 0
        ratings_by_type.append(
            {
                "titleType": title_type,
                "count": int(count),
                "averageRating": round(average_rating, 2),
            }
        )

    genres_by_rating = []
    for genre, count in genre_rating_count.items():
        if count >= min_genre_titles:
            average_rating = genre_rating_sum[genre] / count if count else 0
            genres_by_rating.append(
                {
                    "genre": genre,
                    "count": int(count),
                    "averageRating": round(average_rating, 2),
                }
            )
    genres_by_rating.sort(key=lambda item: (-item["averageRating"], -item["count"], item["genre"]))

    summary = {
        "total_titles": int(total_titles),
        "title_types": [
            {"titleType": title_type, "count": int(count)}
            for title_type, count in type_counts.most_common(top_n)
        ],
        "adult_split": {
            "adult": adult_counts["adult"],
            "non_adult": adult_counts["non_adult"],
        },
        "top_decades": [
            {"decade": int(decade), "count": int(count)}
            for decade, count in decade_counts.most_common(top_n)
        ],
        "top_genres": [
            {"genre": genre, "count": int(count)}
            for genre, count in genre_counts.most_common(top_n)
        ],
        "average_start_year_by_type": [
            {"titleType": title_type, "averageStartYear": average_start_year[title_type]}
            for title_type in sorted(average_start_year, key=lambda key: average_start_year[key])
        ],
        "ratings_by_type": ratings_by_type[:top_n],
        "top_genres_by_rating": genres_by_rating[:top_n],
    }
    return summary


def render_markdown(summary: dict, output_path: Path, *, min_votes: int, min_genre_titles: int, top_n: int) -> None:
    """Write a Markdown report summarizing the exploratory analysis."""
    lines = ["# IMDB Dataset Exploratory Analysis", ""]
    lines.append(f"Total titles processed: **{summary['total_titles']:,}**.")
    lines.append("")

    lines.append("## Distribution by Title Type")
    for item in summary["title_types"]:
        lines.append(f"- {item['titleType']}: {item['count']:,} titles")
    lines.append("")

    total_adult = summary["adult_split"]["adult"] + summary["adult_split"]["non_adult"]
    if total_adult:
        adult_share = summary["adult_split"]["adult"] / total_adult * 100
        lines.append(
            "Adult titles represent {:.1f}% of the catalog ({:,} titles).".format(
                adult_share, summary["adult_split"]["adult"]
            )
        )
        lines.append("")

    lines.append("## Start Year Trends")
    lines.append("Average release year by title type:")
    for item in summary["average_start_year_by_type"]:
        lines.append(f"- {item['titleType']}: {item['averageStartYear']:.1f}")
    lines.append("")

    if summary["top_decades"]:
        lines.append("Most prolific decades (by number of titles):")
        for item in summary["top_decades"]:
            lines.append(f"- {item['decade']}s: {item['count']:,} titles")
        lines.append("")

    if summary["top_genres"]:
        lines.append("## Popular Genres")
        for item in summary["top_genres"]:
            lines.append(f"- {item['genre']}: {item['count']:,} titles")
        lines.append("")

    if summary["ratings_by_type"]:
        lines.append("## Ratings (filtered to titles with >= {} votes)".format(min_votes))
        for item in summary["ratings_by_type"]:
            lines.append(
                f"- {item['titleType']}: average rating {item['averageRating']:.2f} across {item['count']:,} titles"
            )
        lines.append("")

    if summary["top_genres_by_rating"]:
        lines.append(
            "Top genres by average rating (min {} rated titles per genre):".format(
                min_genre_titles
            )
        )
        for item in summary["top_genres_by_rating"]:
            lines.append(
                f"- {item['genre']}: {item['averageRating']:.2f} average rating across {item['count']:,} titles"
            )
        lines.append("")

    lines.append("Report generated using top {} categories for brevity.".format(top_n))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--basics-path",
        type=Path,
        default=Path("data/raw/title.basics.tsv.gz"),
        help="Path to the title.basics.tsv.gz file.",
    )
    parser.add_argument(
        "--ratings-path",
        type=Path,
        default=Path("data/raw/title.ratings.tsv.gz"),
        help="Path to the title.ratings.tsv.gz file.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Number of rows per chunk when streaming the basics file.",
    )
    parser.add_argument(
        "--min-votes",
        type=int,
        default=DEFAULT_MIN_VOTES,
        help="Minimum number of votes required for a title to be included in the ratings analysis.",
    )
    parser.add_argument(
        "--min-genre-titles",
        type=int,
        default=DEFAULT_MIN_GENRE_TITLES,
        help="Minimum number of rated titles required for a genre to be ranked by rating.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help="Number of entries to keep for the top lists.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("analysis/results/imdb_eda_summary.md"),
        help="Markdown file where the textual summary will be saved.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ratings = None
    if args.ratings_path:
        ratings = load_ratings(args.ratings_path, args.min_votes)

    summary = analyze_titles(
        args.basics_path,
        ratings,
        chunk_size=args.chunk_size,
        top_n=args.top_n,
        min_genre_titles=args.min_genre_titles,
    )

    render_markdown(
        summary,
        args.output_md,
        min_votes=args.min_votes,
        min_genre_titles=args.min_genre_titles,
        top_n=args.top_n,
    )

    print(f"Summary written to {args.output_md}")


if __name__ == "__main__":
    main()
