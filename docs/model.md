# EValuator - model

## Overview
The `model` command fits a per-vesicle least-squares geometric model — a sphere, and where the data support it, an ellipsoid — to each labelled EV in an MRC produced by [`evaluator label`](label.md). Each fit is gated on a reliability check (fit residual, surviving point count, and surface coverage), and the command writes both the fitted parameters for every vesicle and a rasterised MRC reconstructing the reliable fits, for visual quality control.

`model` is the geometric-modelling counterpart to [`analyse`](analyse.md): `analyse` measures the raw labelled voxels directly, whereas `model` fits an idealised primitive to the same surface points and reports both the fit and how far it can be trusted. The two commands run independently from the same labelled MRC and do not depend on each other's output.

**`model` requires a pre-labelled MRC.** Unlike `analyse`, it does not auto-label binary segmentations. Every non-zero voxel value is therefore treated as a distinct component, so passing a raw binary mask directly will fit a single model across the entire mask rather than one per vesicle. Always run [`label`](label.md) first.

## Pipeline description
For each labelled component in the input file, the pipeline:
1. Reads the MRC volume and voxel size from the file header (if present; see [Note on voxel size](#note-on-voxel-size) below), and extracts the voxel coordinates of each labelled component in turn.
2. Fits a least-squares sphere (always), and, where at least 9 surface points are available, a least-squares ellipsoid, comparing the two by Bayesian Information Criterion (BIC).
3. Selects the reported model:
   - If the ellipsoid does not improve on the sphere fit (by BIC), the sphere is reported (`sphere`).
   - If the ellipsoid does improve on the fit but its axis ratio is close to 1.0 (below 1.1), it is treated as effectively spherical (`sphere (anisotropy)`).
   - If the ellipsoid's major axis lies within 25° of the beam (z) axis, the apparent elongation is more likely a residual missing-wedge artefact than genuine asphericity, so the sphere is reported instead (`sphere (beam-axis)`).
   - If the ellipsoid fit is numerically degenerate (e.g. the surface points are too flat), the sphere is reported (`sphere (degenerate)`).
   - Otherwise, the ellipsoid is reported (`ellipsoid`).
4. Assesses reliability of the chosen fit against three criteria — relative RMSE, minimum point count, and minimum latitude span (pole-to-pole surface coverage) — all of which must pass for a vesicle to be classed as reliable (see [Reliability thresholds](#reliability-thresholds) below).
5. Writes the per-vesicle results, a fitted MRC (reliable vesicles only, by default), and the resolved run parameters (see [Output](#output) below).

#### Note on voxel size
If the MRC file header contains a valid voxel size (non-zero), all measurements are reported in nanometres. If no voxel size is found, `model` falls back to a scale of 1.0 and a warning is printed to the terminal by the underlying MRC reader. Unlike `analyse`, `model`'s output does not currently include a `measurement_units` field, so results from a header with no voxel size cannot be distinguished from genuine 1.0 nm/voxel data from the output file alone — check the terminal warning, or the source MRC's header, if this matters for your analysis.

## Usage
```
Usage: evaluator model [OPTIONS] INPUT_FILE

Arguments:
  INPUT_FILE   Path to labelled segmentation MRC (i.e. EValuator label output).  [required]

Options:
  -o, --out-dir PATH   Path to output directory (results will be written under '.../evaluator/model/').  [default: .]
  -h, --help            Show this message and exit.
```

Global verbosity options (`-v` / `-vv`) are set on the `evaluator` command itself, and should be included before the `model` subcommand:

```sh
evaluator -v model evaluator/label/tomo_seg_labelled.mrc
evaluator -vv model evaluator/label/tomo_seg_labelled.mrc
```

### Reliability thresholds
All three reliability criteria are editable using a configuration file, but are not currently exposed as command-line flags. Set them under `[model]` in your configuration file (see the [`config` documentation](config.md) for more information):

- `rmse_relative_max` (default `0.15`): maximum allowed ratio of fit RMSE to fitted radius. Fits at or above this ratio fail the reliability gate.
- `min_points` (default `20`): minimum number of surviving surface points required for a fit to be considered reliable.
- `min_latitude_span_deg` (default `60`): minimum pole-to-pole coverage, in degrees, that the surviving surface points must span. Fits below this fail the reliability gate.

## Output

Results are written under the output directory (default: current working directory) to `evaluator/model/`:

- `model_results.json` (or `.csv`, depending on `format` under `[output]` in your configuration file) — one entry per successfully fitted vesicle.
- `model_fitted.mrc` — a rasterised reconstruction of the fitted primitives, using the same label values as the input. Only vesicles passing the reliability gate are included; this is not currently configurable.
- `params.toml` — the resolved `[model]` parameters used for this run.

### Output fields

The following fields are reported per vesicle (as JSON object keys, or as CSV columns if `format = "csv"`):

Field | Description | Type / units
--|--|--
`label_id` | Unique integer identifier for the EV, matching its label in the input MRC | integer
`source_file` | Filename of the input labelled MRC | string
`chosen_model`<sup>**1**</sup> | Which geometric model was used for the reported measurements | `sphere`, `ellipsoid`, `sphere (anisotropy)`, `sphere (beam-axis)`, or `sphere (degenerate)`
`centre` | Fitted centre coordinates `[x, y, z]` of the chosen model | nm<sup>**2**</sup>
`radius` | Fitted radius (sphere), or mean of the three fitted radii (ellipsoid) | nm
`radii`<sup>**3**</sup> | The three fitted ellipsoid semi-axis lengths, if an ellipsoid was chosen | nm, or `null` for sphere fits
`orientation`<sup>**3**</sup> | 3×3 rotation matrix defining ellipsoid axis orientation, if an ellipsoid was chosen | unitless, or `null` for sphere fits
`rmse_nm` | Root-mean-square geometric residual of the chosen model fit | nm
`bic_sphere` | Bayesian Information Criterion of the sphere fit | unitless
`bic_ellipsoid` | Bayesian Information Criterion of the ellipsoid fit | unitless, or `null` if an ellipsoid fit was not attempted
`reliability`<sup>**4**</sup> | Nested object recording the reliability gate outcome | see footnote 4
`beam_axis`<sup>**5**</sup> | Nested object recording the beam-axis guard outcome | see footnote 5, or `null` if not applicable
`sphere_fit`<sup>**6**</sup> | The sphere fit's own centre/radius/RMSE/BIC, reported regardless of which model was chosen | see footnote 6
`ellipsoid_fit`<sup>**6**</sup> | The ellipsoid fit's own centre/radii/orientation/RMSE/BIC, if attempted | see footnote 6, or `null` otherwise

<sup>**1**</sup> See [Pipeline description](#pipeline-description) above for what each value means and when it is selected.

<sup>**2**</sup> Assumes the input MRC has a valid voxel size header — see [Note on voxel size](#note-on-voxel-size).

<sup>**3**</sup> Only populated when `chosen_model` is `ellipsoid`.

<sup>**4**</sup> `reliability` contains: `is_reliable` (bool, the overall gate outcome), `relative_rmse` (float, fit RMSE ÷ radius), `rmse_ok` (bool), `count_ok` (bool), `lat_span_deg` (float, pole-to-pole coverage in degrees), `span_ok` (bool).

<sup>**5**</sup> `beam_axis` is only populated when an ellipsoid fit was attempted and BIC favoured it over the sphere; it contains `beam_axis_flagged` (bool), `major_axis_angle_from_z_deg` (float), `beam_axis_tol_deg` (float, fixed at 25° and not currently configurable).

<sup>**6**</sup> `sphere_fit` contains `centre`, `radius`, `rmse_nm`, `bic`. `ellipsoid_fit` contains `centre`, `radii`, `orientation`, `rmse_nm`, `bic`. These are reported for both fit attempts regardless of `chosen_model`, so the non-chosen fit's numbers remain available for comparison.

**CSV output:** if `format = "csv"` is set under `[output]` in your configuration, the nested fields (`centre`, `radii`, `orientation`, `reliability`, `beam_axis`, `sphere_fit`, `ellipsoid_fit`) are JSON-encoded as strings within their CSV cell — parse them with `json.loads()` (or equivalent) to recover the structured data. In this mode, run parameters are written separately to `params.toml` rather than being inlined alongside the results.

<br>

---
<p align="right"><a href="#evaluator---model">^ Back to top</a></p>
