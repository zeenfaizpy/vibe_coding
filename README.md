# IMDB Dataset Exploration

This project downloads public IMDB datasets, explores the core title metadata, and records the main findings from the analysis. The goal was to understand what is available at [datasets.imdbws.com](https://datasets.imdbws.com/) and highlight trends within the catalogue.

## Data acquisition

The script [`scripts/download_imdb.py`](scripts/download_imdb.py) streams gzip-compressed TSV files directly from IMDB. By default it retrieves:

- `name.basics.tsv.gz`
- `title.basics.tsv.gz`
- `title.principals.tsv.gz`
- `title.ratings.tsv.gz`

Files are saved to `data/raw/` (which is gitignored). Each TSV uses tab separators and the value `\N` to denote missing data. Additional dataset files can be requested by passing their names to the script.

## Exploratory analysis

The exploratory script [`analysis/imdb_eda.py`](analysis/imdb_eda.py) focuses on `title.basics` and `title.ratings`. It loads the large tables in chunks, normalises missing values, and aggregates high-level metrics. Key configuration options include the chunk size, the minimum number of votes for ratings analysis, and the number of top categories reported. Results are written to `analysis/results/imdb_eda_summary.md`.

### Catalogue structure

- IMDB lists **11,912,581 titles**; 77% of the entries are individual TV episodes, with shorts, movies, and direct-to-video releases making up most of the remainder.【F:analysis/results/imdb_eda_summary.md†L1-L15】
- Only **3.3%** of titles are flagged as adult content (≈389k entries), so most of the dataset is general audience material.【F:analysis/results/imdb_eda_summary.md†L17-L20】
- Release dates skew recent: the 2010s alone contribute 3.9M titles, and the 2020s already account for 2.6M entries, underscoring how rapidly TV and streaming catalogues have expanded.【F:analysis/results/imdb_eda_summary.md†L25-L33】
- The typical release year differs across formats—stand-alone movies cluster around the mid-1990s while TV mini-series and pilot episodes lean into the 2010s—showing how newer distribution formats dominate serialized content.【F:analysis/results/imdb_eda_summary.md†L21-L24】

### Genre mix and ratings

- Drama and Comedy are the most common genres (3.4M and 2.3M titles respectively), followed by large volumes of Talk-Show, Short, Documentary, and News programming.【F:analysis/results/imdb_eda_summary.md†L35-L45】
- Restricting to titles with at least 5,000 user votes reveals that TV episodes and video games receive the highest average ratings (8.39 and 8.53 respectively). Feature films settle around a 6.5 average, reflecting a broader quality spectrum.【F:analysis/results/imdb_eda_summary.md†L47-L58】
- Genres with consistently high ratings include Animation (7.69), Documentary (7.42), and History (7.29) once we require at least 200 rated titles per genre, suggesting strong fan sentiment for niche, information-rich content.【F:analysis/results/imdb_eda_summary.md†L60-L66】

## Reproducing the workflow

1. Install dependencies: `pip install -r requirements.txt`
2. Download the datasets: `python scripts/download_imdb.py`
3. Run the analysis: `python analysis/imdb_eda.py`

The analysis script parameters can be tweaked to explore different slices (e.g., lower the vote threshold or widen the number of categories reported).
