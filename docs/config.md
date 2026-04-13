# EValuator - config

## Overview
The `config` command manages EValuator's configuration files. EValuator ships with a bundled default configuration file (`config.toml`) which controls default values for filtering thresholds, visualisation settings, and plot styles. A user-specific configuration file can be created in the OS configuration directory to override any of these defaults without modifying the package itself.

The user configuration file is stored at the following path depending on the operating system:
| OS | Path |
|---|---|
| Linux / macOS | `~/.config/evaluator/config.toml` |
| Windows | `%APPDATA%\evaluator\config.toml` |

Running `evaluator config` without a subcommand reports whether a user configuration file exists, and shows its current settings if so.

## Usage

```
Usage: evaluator config [COMMAND]

Config Commands:
  init    Create a user config file populated with default settings.
  exists  Report whether a user config file exists.
  list    Print current config values against EValuator defaults.
  verify  Check all expected keys are present in the user config file.
  reset   Overwrite the user config file with EValuator default values.
```

## Subcommands

### `init`

Creates a user configuration file at the OS configuration directory, populated with EValuator's built-in default values. This is the recommended starting point for customising EValuator's behaviour.

```sh
evaluator config init
```

If a user configuration file already exists, `init` will not overwrite it. Run `evaluator config reset` instead to restore defaults.

---

### `exists`

Reports whether a user configuration file is present at the expected path, and prints that path.

```sh
evaluator config exists
```

Exits with a non-zero code if no user configuration file is found.

---

### `list`

Prints a table of all current configuration values, comparing them against the EValuator built-in defaults. Keys whose user-set value differs from the default are highlighted.

```sh
evaluator config list
```

If no user configuration file exists, the table reflects the built-in defaults.

---

### `verify`

Checks that all expected configuration keys are present in the user configuration file, and that no unexpected keys are present, by comparing against the bundled default configuration. Useful after manually editing `config.toml` or after upgrading EValuator.

```sh
evaluator config verify
```

Exits with a non-zero code if any missing or unexpected keys are found, listing them in the terminal output. Run `evaluator config reset` to restore a valid configuration.

---

### `reset`

Overwrites the user configuration file with EValuator's built-in default values. Includes a confirmation prompt by default; use `--force` to skip this.

```sh
evaluator config reset
evaluator config reset --force
```

**Options:**

| Option | Description |
|---|---|
| `--force` | Skip the confirmation prompt and overwrite immediately. |

---

## Configuration file reference

The default `config.toml` is shown below, with all available keys and their default values.

```toml
# Global defaults
[global]
verbose = false
debug = false

# Membrane filtering defaults
[filter]
closure_fill_threshold = 0.05
max_diameter_nm = 500.0
min_diameter_nm = 20.0
membrane_thickness_nm = 7

# Labelling defaults
[label]
overlay_style = "both"    # valid options: both, filled, outlined
n_slices = 9              # default number of slices in tiled overlay panel

# Matplotlib style defaults
[mplstyle]
colourmap = "tab20"       # matplotlib colourmap for component label colours
alpha_fill = 0.35         # opacity of filled overlay regions
contour_linewidth = 1.0   # line width for contour overlays
label_fontsize = 6        # font size for component label text annotations
figure_dpi = 300          # output image resolution in dots per inch

# Visualisation defaults
[visualisation]
fps = 45
downsample = 2
```

Each `[section]` corresponds to the part of EValuator that uses those settings:

- **`[filter]`**: default values for `analyse` filtering options (`--min-diam`, `--max-diam`, `--fill-threshold`) and the membrane thickness assumption used to convert diameter limits to voxel-count limits.
- **`[label]`**: default values for the `visualise overlay` tiled panel options.
- **`[mplstyle]`**: controls the appearance of all matplotlib-generated outputs (overlay images, Z-stack movies).
- **`[visualisation]`**: default frame rate for Z-stack movies and downsampling factor for isometric renders.

<br>

---
<p align="right"><a href="#evaluator---config">^ Back to top</a></p>
