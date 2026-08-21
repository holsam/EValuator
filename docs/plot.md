# EValuator - plot

## Overview
The `plot` command generates plots and summary tables from [`analyse`](analyse.md) output and/or [`model`](model.md) outputs. Each run produces one or more independent sections (depending on provided results), each writing SVG plots and `.xlsx` summary statistics under `evaluator/plot/<section>`.

`plot` requires R to be installed, and either available on `PATH` or passed using the `--rscript` option.

## Pipeline description
For a given run, the pipeline:
1. Resolves `--analyse`/`--model` into one or more runs (each option accepts either a direct result file or a sample sheet).
2. Determines which sections are runnable for the given inputs and which were requested on command line.
3. Dispatches each section to its own R script via `Rscript`, writing outputs to `evaluator/plot/<section>/`. A section directory that already exists is skipped unless `--overwrite` is given. A section that fails (non-zero `Rscript` exit) is logged as a warning, but should not stop the remaining sections from running.
4. Writes `evaluator/plot/index.md`, linking every section that completed successfully and `evaluator/plot/params.toml`, the resolved `[plot]` parameters used for the run.

## Usage
```
Usage: evaluator plot [OPTIONS]

Options:
  --analyse PATH        Path to an analyse results CSV, or a sample sheet referencing multiple.
  --model PATH           Path to a model results file (JSON or CSV), or a sample sheet referencing multiple.
  -o, --out-dir PATH     Path to output directory, outputs written under '.../evaluator/plot/'.  [default: .]
  --section TEXT         Section(s) to run: distributions, qc, scatter, concordance, compare (repeatable).
  --all                  Run every applicable section.
  --overwrite            Overwrite existing section outputs instead of skipping them.
  --rscript PATH         Path to the Rscript binary (default: resolved from PATH).
  -h, --help              Show this message and exit.
```

At least one of `--analyse`/`--model` must be provided. Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `plot` subcommand:

```sh
evaluator -v plot --analyse evaluator/results/analyse/evaluator-analyse_results.csv --all
evaluator -vv plot --analyse evaluator/results/analyse/evaluator-analyse_results.csv --all
```

### `--section` and `--all`
By default (no `--section`, no `--all`), the sections listed under `[plot].default_sections` in the resolved configuration file are run. `--section` may be repeated to run a specific subset, or `--all` can be used to run every runnable section.

## Sections

Section | Requires | Outputs
--|--|--
`distributions` | `--analyse` | A density + rug plot per morphology feature (`<feature>_density.svg`), and `summary_stats.xlsx` (*n*, mean, median, sd, p5, p95 per feature)
`qc` | `--analyse` | `count_per_tomogram.svg` (EV count per tomogram), `closure_pass_rate.svg` (fraction `is_enclosed` per tomogram), `closure_fill_ratio_distribution.svg` (with the configured flag threshold marked), and `qc_summary.xlsx` (per-tomogram EV count, pass rate, median fill ratio, count flagged below threshold)
`scatter` | `--analyse` | A scatter plot with fitted trend line per feature pair (`equiv_diameter_nm` vs `lumen_volume`, `surface_area` vs `lumen_volume`, `aspect_ratio` vs `equiv_diameter_nm`), and `scatter_stats.xlsx` (Pearson/Spearman correlation, slope, slope SE per pair)
`concordance` | `--analyse` **and** `--model` | See [Concordance](#concordance) below.
`compare` | Sample sheet with more than one distinct `group` (multi-sample mode) | Per-feature violin+box plots by group (`violin_<feature>.svg`), a PCA plot across standardised features (`pca.svg`, only if ≥3 complete-case rows and ≥2 features are available), and `group_summary.xlsx` (per-group n, mean, median per feature)

### Concordance
`concordance` provides a comparison of `model`'s least-squares-fitted geometry and the raw voxel measurements that `analyse` produces. 

Rows are joined on `analyse`'s `(tomogram, label)` against `model`'s `(source_file,
label_id)`, matching `source_file`'s basename against `tomogram`, therefore both must have been run against the same labelled MRC(s) for rows to match. Only matched rows are plotted; `concordance_stats.xlsx` reports `n_matched`, `n_analyse_only`, and `n_model_only` so unmatched counts are visible.

Produces, per matching vesicle set:
- `model_vs_equiv_diameter_nm.svg` and `model_vs_major_axis_diameter.svg` — `model`'s fitted diameter (`2 × radius`) plotted against each of `analyse`'s two independent diameter estimates, with a `y = x` reference line.
- `reliability_vs_closure.svg` — whether `model`'s `reliability.is_reliable` gate tracks `analyse`'s independently-measured `closure_fill_ratio`.
- `fit_rmse_vs_enclosed.svg` — whether `model`'s fit RMSE tracks `analyse`'s `is_enclosed`.
- `concordance_stats.xlsx` — match counts (above) plus Pearson correlation between `model`'s fitted diameter and each of `analyse`'s two diameter estimates, and the reliable-fit pass rate among matched rows.

## Sample sheets (multi-sample mode)
`--analyse` and/or `--model` may point to a sample sheet instead of a single result file, which is a `.tsv` or `.txt` file with a header row containing `sample_id`.

Column | Required | Description
--|--|--
`sample_id` | Yes | Unique identifier for the sample/run; joins rows across the `--analyse` and `--model` sheets when both are sheets
`path` | No | Path to that sample's result file. If omitted and the *other* option's value is a single file (not a sheet), that single file is treated as applying to every sample on this side
`group` | No | Group label, used by the `compare` section. `compare` only becomes runnable when more than one distinct `group` value is present across the sheet.
`replicate` | No | Optional integer replicate number; parsed but not currently used by any section

If both `--analyse` and `--model` are sheets, rows are matched by `sample_id`; a `sample_id` present in only one sheet gets `None` for the missing side. If only one side is a sheet, every sample on that side is paired with the other side's single (non-sheet) file, if one was given.

## R prerequisites
`plot` requires `Rscript` to render plots and write spreadsheets, as well as requires the following R packages to be installed: `tidyverse`, `jsonlite`, `openxlsx`,
`viridisLite`. 

By default, `plot` resolves `Rscript` from `PATH`. If R isn't on `PATH` (e.g. an `renv`/`conda` R install), pass its location explicitly with `--rscript`:
```sh
evaluator plot --analyse evaluator/results/analyse/evaluator-analyse_results.csv --all --rscript /path/to/Rscript
```

## Output
Results are written under the output directory (default: current working directory) to
`evaluator/plot/`:

- `<section>/`: one directory per completed section, containing that section's SVG plots and `.xlsx` summary table(s)
- `index.md`: links to every section that completed successfully in this run
- `params.toml`: the resolved `[plot]` parameters used for this run

### Configuration
`plot` reads the following default values from the configuration file's `[plot]` section:
- `default_sections` (default `["distributions", "qc", "scatter"]`): sections run when
  neither `--section` nor `--all` is given.
- `fill_ratio_flag_threshold` (default `0.05`): `closure_fill_ratio` values below this are marked in the `qc` section's fill-ratio histogram and counted in `qc_summary.xlsx`.

<br>

---
<p align="right"><a href="#evaluator---plot">^ Back to top</a></p>
