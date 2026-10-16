# EValuator - plot

## Overview
The `plot` command generates plots and summary tables from [`analyse`](analyse.md) output and/or [`model`](model.md) outputs. Each run produces one or more independent sections (depending on provided results), each writing SVG plots and `.xlsx` summary statistics under `evaluator/plot/<section>`.

## Pipeline description
For a given run, the pipeline:
1. Resolves `--analyse`/`--model` into one or more runs (each option accepts either a direct result file or a sample sheet).
2. Determines which sections are runnable for the given inputs and which were requested on command line.
3. Runs each section, writing outputs to `evaluator/plot/<section>/`. A section directory that already exists is skipped unless `--overwrite` is given. A section that fails is logged as a warning, but should not stop the remaining sections from running.
4. Writes `evaluator/plot/index.md`, linking every section that completed successfully and `evaluator/plot/params.toml`, the resolved `[plot]` parameters used for the run.

## Usage
```
Usage: evaluator plot [OPTIONS]

Options:
  --analyse PATH         Path to an analyse results CSV, or a sample sheet referencing multiple.
  --model PATH           Path to a model results file (JSON or CSV), or a sample sheet referencing multiple.
  -o, --out-dir PATH     Path to output directory, outputs written under '.../evaluator/plot/'.  [default: .]
  --section TEXT         Section(s) to run: distributions, qc, scatter, concordance, compare (repeatable).
  --all                  Run every applicable section.
  --overwrite            Overwrite existing section outputs instead of skipping them.
  --include-flagged      Include components flagged as non-vesicle-like instead of excluding them.
  --agreement TEXT,TEXT  Bland-Altman plot for a pair of measurements (repeatable).
  -h, --help             Show this message and exit.
```

At least one of `--analyse`/`--model` must be provided. Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `plot` subcommand:

```sh
evaluator -v plot --analyse evaluator/results/analyse/evaluator-analyse_results.csv --all
evaluator -vv plot --analyse evaluator/results/analyse/evaluator-analyse_results.csv --all
```

### `--section` and `--all`
By default (no `--section`, no `--all`), the sections listed under `[plot].default_sections` in the resolved configuration file are run. `--section` may be repeated to run a specific subset, or `--all` can be used to run every runnable section.

### QC filtering
Any vesicles where `analyse`'s `is_vesicle_like` column is `False` are excluded before computing any distribution, statistic or plot. The number of dropped rows and a breakdown of the reasons for exclusion are logged automatically. To include these vesicles in outputs, use the `--include-flagged` option.

### Caveats
`scatter`, `correlations` and `compare` pool every vesicle, irrespective of source tomogram/sample, and treat each as an independent observation. No clustering-adjusted tests are applied, so statistics should be treated as descriptive only. `tomogram` (and `sample_id` for `compare`) are kept in outputs for further analysis which accounts for this clustering.

## Sections

Section | Requires | Outputs
--|--|--
`distributions` | `--analyse` | A histogram per morphology feature (`<feature>_histogram.svg`), and `summary_stats.xlsx` (*n*, mean, median, sd, p5, p95 per feature)
`qc` | `--analyse` | `count_per_tomogram.svg`, `closure_pass_rate.svg`, `closure_fill_ratio_distribution.svg` (configured flag threshold marked), and `qc_summary.xlsx`
`scatter` | `--analyse` | A scatter plot with fitted trend line and R^2 annotation per feature pair (`<x>_vs_<y>.svg`), and `scatter_stats.xlsx` (Pearson/Spearman correlation, slope, slope SE, R^2, *n* per pair)
`correlations` | `--analyse` | `correlation_spearman.svg` and `correlation_pearson.svg` heatmaps across the morphology features, and `correlations.xlsx`
`concordance` | `--analyse` **and** `--model` | See [Concordance](#concordance) below.
`reliability` | `--analyse` **and** `--model` | `reliability.svg` (fit RMSE against closure fill ratio, coloured by `reliability.is_reliable`) and `reliability_summary.xlsx`
`agreement` | `--analyse` **and** `--model`; runs when `--agreement` is given | See [Agreement](#agreement) below.
`compare` | Sample sheet with more than one distinct `group` | Per-feature violin+box plots by group (`violin_<feature>.svg`), `pca.svg` (only if at least 3 complete-case rows and 2 features), and `group_summary.xlsx`

### Concordance
`concordance` provides a comparison of `model`'s least-squares-fitted geometry and the raw voxel measurements that `analyse` produces. 

Rows are joined on `analyse`'s `(tomogram, label)` against `model`'s `(source_file, label_id)`, matching `source_file`'s basename against `tomogram`, therefore both must have been run against the same labelled MRC(s) for rows to match. Only matched rows are plotted; `concordance_stats.xlsx` reports `n_matched`, `n_analyse_only`, and `n_model_only` so unmatched counts are visible.

Produces `model_vs_equiv_diameter_nm.svg` and `model_vs_major_axis_diameter.svg` (`model`'s fitted diameter against each `analyse` diameter, with a `y = x` line, trend line and bias/RMSE annotation) and `concordance_stats.xlsx` (bias, RMSE and Pearson correlation per diameter, plus `n_matched`, `n_analyse_only`, `n_model_only`). With the default QC filter, `model` rows for components `analyse` flagged are counted in `n_model_only`.

### Agreement
`--agreement A,B` creates a Bland-Altman plot (difference `A - B` against the mean, with bias and 95% limits of agreement) for each measurement pair, written to `agreement/<A>_vs_<B>.svg`, with `agreement_stats.xlsx`. The option can be repeated to produce several Bland-Altman plots:
```sh
evaluator plot --analyse analyse.csv --model model.json --agreement equiv_diameter_nm,model_diameter_nm --agreement major_axis_diameter,model_diameter_nm
```

`A` and `B` are column names from the joined analyse and model results. Pairs naming a missing column are skipped with a warning. `--section agreement` or `--all` without `--agreement` plots `equiv_diameter_nm,model_diameter_nm`.

## Sample sheets (multi-sample mode)
`--analyse` and/or `--model` may point to a sample sheet instead of a single result file, which is a `.tsv` or `.txt` file with a header row containing `sample_id`.

Column | Required | Description
--|--|--
`sample_id` | Yes | Unique identifier for the sample/run; joins rows across the `--analyse` and `--model` sheets when both are sheets
`path` | No | Path to that sample's result file. If omitted and the *other* option's value is a single file (not a sheet), that single file is treated as applying to every sample on this side
`group` | No | Group label, used by the `compare` section. `compare` only becomes runnable when more than one distinct `group` value is present across the sheet.
`replicate` | No | Optional integer replicate number; parsed but not currently used by any section

If both `--analyse` and `--model` are sheets, rows are matched by `sample_id`; a `sample_id` present in only one sheet gets `None` for the missing side. If only one side is a sheet, every sample on that side is paired with the other side's single (non-sheet) file, if one was given.

## Output
Results are written under the output directory (default: current working directory) to
`evaluator/plot/`:

- `<section>/`: one directory per completed section, containing that section's SVG plots and `.xlsx` summary table(s); in multi-sample mode, per-sample sections are split into `<section>/<sample_id>/`
- `index.md`: links to every section that completed successfully in this run
- `params.toml`: the resolved `[plot]` parameters used for this run

### Configuration
`plot` reads the following default values from the configuration file's `[plot]` section:
- `default_sections` (default `["distributions", "qc", "scatter", "correlations"]`): sections run when neither `--section` nor `--all` is given
- `fill_ratio_flag_threshold` (default `0.05`): `closure_fill_ratio` values below this are marked in the `qc` fill-ratio histogram and counted in `qc_summary.xlsx`
- `theme` (default `"Okabe-Ito"`): figure colours; one of the viewer's named themes
- `bin_width` (default `25.0`): histogram bin width in feature units, anchored at 0; `0` for automatic bins
- `[plot.bin_width_overrides]`: per-feature bin widths replacing `bin_width`
- `scatter_pairs`: the `[x, y]` feature pairs drawn by `scatter`

<br>

---
<p align="right"><a href="#evaluator---plot">^ Back to top</a></p>
