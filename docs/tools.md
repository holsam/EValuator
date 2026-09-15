# EValuator - tools

## Overview
`evaluator tools` groups miscellaneous utilities that sit outside the main pipeline: animation stubs, accuracy benchmarks, pipeline diagram rendering, and R dependency management.

```
evaluator tools --help
  animate     Animation of pipeline geometric principles. [NOT IMPLEMENTED]
  benchmark   Accuracy benchmarks for missing-wedge correction and geometric proxies
  diagram     Render the EValuator pipeline diagram
  r-deps      Check/install EValuator's required R dependencies
```

## `evaluator tools animate`
This command is currently a stub, and will only print a not-implemented notice and before exiting.

## `evaluator tools benchmark`
Runs synthetic accuracy benchmarks used during development.

### `evaluator tools benchmark missing-wedge`
Benchmarks missing-wedge correction/fitting accuracy across a range of synthetic EV diameters.

| Option | Default | Description |
|---|---|---|
| `-o, --output-dir` | `./out/benchmark` | Output directory for benchmark results |
| `--min-diameter` | benchmark default | Minimum diameter to benchmark against |
| `--max-diameter` | benchmark default | Maximum diameter to benchmark against |
| `--diameter-step` | benchmark default | Step (nm) between benchmarked diameters |
| `--n-replicates` | benchmark default | Number of replicates per nominal diameter |
| `--voxel-size-nm` | benchmark default | Voxel size to use for synthetic EVs |
| `--tilt-range` | benchmark default | Tilt range to use for synthetic tilt series |
| `--diameter-jitter` | benchmark default | Jitter to add for varying nominal diameter |
| `--shape-jitter` | benchmark default | Jitter to add for varying EV shape |
| `--seed` | benchmark default | Seed for the random generator |

Defaults are defined in `evaluator.commands.tools.benchmark_missing_wedge.defaults`.

### `evaluator tools benchmark geometric-proxy`
Benchmarks the `estimateCentroidRadius` geometric proxy (naive vs isotropy-aware bounding box) across partial spherical caps and equatorial bands.

| Option | Description |
|---|---|
| `-o, --output-dir` | Output directory for benchmark results (default `./out/benchmark`) |
| `--min-cap-angle` / `--max-cap-angle` / `--cap-angle-step` | Polar-cap half-angle (deg) range to benchmark against |
| `--min-band-width` / `--max-band-width` / `--band-width-step` | Equatorial-band half-width (deg) range to benchmark against |
| `--n-replicates` | Number of replicates per completeness value |
| `--radius-nm` | True sphere radius for synthetic point clouds |
| `--n-points` | Number of points sampled per synthetic point cloud |
| `--seed` | Seed for the random generator |
| `--horizontal` | Transpose the output diagram to 4x3 instead of 3x4 |

Defaults are defined in `evaluator.commands.tools.benchmark_geometric_proxy.defaults`.

## `evaluator tools diagram`

### `evaluator tools diagram pipeline`
Renders a PNG diagram of the EValuator pipeline, using real `label`/`model` output on test fixtures alongside synthetic partial-coverage (band/cap) examples.

| Option | Default | Description |
|---|---|---|
| `-o, --output` | `diagram_pipeline.defaults.OUTPUT` | Output PNG path for the pipeline diagram |
| `--downsample` | `diagram_pipeline.defaults.DOWNSAMPLE` | Voxel downsample factor for rendering |

## `evaluator tools r-deps`

Manages the R packages required by `evaluator plot`'s `Rscript`-based rendering (see [`plot`](plot.md)).

### `evaluator tools r-deps check`
```sh
evaluator tools r-deps check [--rscript Rscript]
```
Runs `check_deps.R` via the configured `Rscript` binary and prints installed/missing R packages.

### `evaluator tools r-deps install`
```sh
evaluator tools r-deps install [--rscript Rscript]
```
Checks for missing R packages and, after an interactive `y/N` confirmation, installs them via `install_deps.R`, streaming installer output.

Both subcommands accept `--rscript` (default `Rscript`) to point at a specific `Rscript` binary.
