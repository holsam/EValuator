# EValuator - config

## Overview
The `config` command creates and edits EValuator's configuration file. The file is stored inside the output directory alongside results, so each project can have its own settings and the configuration that produced a given set of outputs is always co-located with them.

The configuration file is located at `evaluator/config.toml` where `evaluator/` is the output directory that EValuator writes into. Results for each command sit in subdirectories of the same tree:
```
evaluator/
  config.toml
  label/
  repair/
  analyse/
  visualise/
```

EValuator ships with built-in default values for all settings. If no `config.toml` exists when a pipeline command runs, one is created automatically from those defaults and a notice is printed. The `config` command is provided for explicitly creating or editing the configuration file directly.

## Usage

```
Usage: evaluator config [OPTIONS] PATH

Arguments:
  PATH               Path to directory or configuration file path

Options:
  -s, --stepwise     Edit values through stepwise terminal prompting instead of in editor
  --help             Show this message and exit.
```

## Path resolution

`evaluator config` accepts any of the following as `PATH` and resolves it to a config file in a consistent way:

`PATH` | Configuration resolution
-- | --
An existing `.toml` file | `PATH` is edited directly
An `evaluator/` directory | `<PATH>/config.toml` within the passed directory is edited
A directory containing `evaluator/config.toml` | `<PATH>/evaluator/config.toml` is edited
A directory with no `evaluator` directory or `config.toml` | `<PATH>/evaluator/config.toml` is created from defaults, with a prompt to edit

Resolution stops at the first matching rule, so pointing at a directory that is already an `evaluator/` directory will never nest a second `evaluator/` inside it.

## Behaviour

**Existing config found.** The file opens immediately in `$EDITOR` (or using interactive prompts with `-s`/`--stepwise`).

**No config found.** The file is created from built-in defaults, and a prompt asks:
```
Edit it now? [Y/n]:
```
Answering yes opens the editor. Answering no leaves the configuration file in place with default values.

**Automatic creation during pipeline runs.** If an EValuator command (e.g. `label`, `analyse`) is run in a directory with no `config.toml`, one is created silently from defaults and the pipeline continues.

## Editing modes

### Open in `$EDITOR` (default)

```sh
evaluator config
evaluator config path/to/project
```

Opens the config file in whatever editor is set in the `$EDITOR` environment variable (the same behaviour as `git config --edit`). Save and close the file to apply changes. If the saved file fails validation, a warning is printed but no exception is raised.

### Stepwise in terminal (with `-s`/`--stepwise`)

```sh
evaluator config -s
evaluator config -s path/to/project
```

Walks through each setting one by one, printing the current value as the default. Press Enter to keep a value or type a new one. Comments and file layout are preserved. Array-type settings are skipped and must be edited in the file directly. Changes are validated before being written. If any value fails validation, the session is aborted and the original file is left unchanged.

## CLI overrides
Every pipeline command accepts flags that override individual config values for a single run without modifying `config.toml`. For example:

```sh
evaluator analyse labelled_segmentation.mrc --min-diameter 50 --fill-threshold 0.8
```

The effective values used for each run are recorded in `evaluator/<command>/params.toml` alongside the results for reference.


## Configuration file reference
The default `config.toml` is shown below with all available keys and their default values. Each section corresponds to the command or feature that uses those settings.

```toml
# Global logging defaults
[log]
verbose = false
debug = false

# Output format configuration default
[output] 
format = "json"

# Label command default configuration parameters
[label]
min_arc_coverage = 0.30
merge_centre_tol_factor = 1.5
merge_radius_tol_pct = 0.30
maximum_diameter_nm = 500.0
minimum_diameter_nm = 20.0
membrane_thickness_nm = 7
max_workers = 0

# Model command default configuration parameters
[model]
rmse_relative_max = 0.15
min_points = 20
min_latitude_span_deg = 60
max_workers = 0

# Analyse command default configuration parameters
[analyse]
fill_threshold = 0.05
max_workers = 0
qc_max_sphere_rmse_rel = 0.25
qc_max_aspect_ratio = 2.5
qc_min_solidity = 0.10
qc_min_arc_coverage = 0.50
qc_max_fit_points = 4000

# Plot command default configuration parameters
[plot]
default_sections = ["distributions", "qc", "scatter"]
fill_ratio_flag_threshold = 0.05

# Visualise command default configuration parameters
[visualise]
overlay_style = "both"          # style of overlay to use (valid options: both, filled, contours)
n_slices = 9                    # default number of slices in tiled panel
fps = 45
downsample = 2
colourmap = "tab20"             # matplotlib colormap used to assign colours to component labels
alpha_fill = 0.35               # opacity of filled overlay regions
contour_linewidth = 1.0         # line width for contour overlays
label_fontsize = 6              # font size for component label text annotations
figure_dpi = 300                # output image resolution in dots per inch
max_workers = 0
```

Section reference:

- **`[log]`**: verbosity and debug output, applied across all commands.
- **`[label]`**: default values for `label` command filtering options (`--min-diam`, `--max-diam`), the membrane thickness assumption used to convert diameter limits to voxel-count limits.
- **`[analyse]`**: — default values for `analyse` filtering options (`--fill-threshold`), and the vesicle-vs-debris QC thresholds (`qc_max_sphere_rmse_rel`, `qc_max_aspect_ratio`, `qc_min_solidity`, `qc_min_arc_coverage`, `qc_max_fit_points`).
- **`[model]`**: default values for the `model` reliability gate (`rmse_relative_max`, `min_points`, `min_latitude_span_deg`).
- **`[label]`**: default values for `visualise` commands: overlay styles, panel tiling, appearance of all matplotlib-generated outputs (overlay images, Z-stack movies), frame rate for Z-stack movies and downsampling factor for isometric renders.

Unknown keys in any section are rejected at load time, and EValuator will raise a `ConfigError` naming the unknown key. `evaluator config` can then be run to reopen the file and correct it.


## Examples

```sh
# Set up config for a new project in the current directory
evaluator config

# Set up config for a project in a specific directory
evaluator config ~/data/experiment_01

# Edit an existing config interactively
evaluator config -i ~/data/experiment_01

# Point directly at a config file
evaluator config ~/data/experiment_01/evaluator/config.toml
```

<br>

---
<p align="right"><a href="#evaluator---config">^ Back to top</a></p>
