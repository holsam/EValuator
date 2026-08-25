'''
=======================================
EValuator: GEOMETRIC PROXY BENCHMARKING SCRIPT SUMMARY FUNCTIONS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import matplotlib.pyplot as plt, numpy as np, pandas as pd

# ====================
# Import internal utilities
# ====================
from evaluator.commands.tools.benchmark_geometric_proxy import defaults

# ====================
# Define constants
# ====================
CLOUD_TYPE_LABELS = {'polar_cap': 'Polar cap', 'equatorial_band': 'Equatorial band'}
METHOD_COLOURS = {'naive bounding box': 'tab:red', 'isotropy-aware bounding box': 'tab:blue'}

# ====================
# Define summary functions
# ====================
# -- summarise_errors: returns DataFrame of per-method, per-cloud-type, per-completeness error statistics
def summarise_errors(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Compute per-method radius/centre error statistics, grouped by cloud type and completeness, pooling across replicates
    '''
    rows = []
    for (cloud_type, completeness_deg), group in df.groupby(['cloud_type', 'completeness_deg']):
        for name, (radius_col, _) in defaults.METHODS.items():
            radius_err_pct = 100 * (group[radius_col] - group['true_radius_nm']).abs() / group['true_radius_nm']
            centre_err = group[f'{radius_col.split("_")[0]}_centre_error_nm']
            rows.append({
                'cloud_type': cloud_type,
                'completeness_deg': completeness_deg,
                'method': name,
                'mean_abs_radius_error_pct': float(radius_err_pct.mean()),
                'mean_centre_error_nm': float(centre_err.mean()),
            })
    return pd.DataFrame(rows)

# -- _sphere_wireframe: returns tuple of ndarray x,y,z for a wireframe sphere at the given centre/radius
def _sphere_wireframe(centre: np.ndarray, radius: float, n: int = 20):
    u = np.linspace(0, 2 * np.pi, n)
    v = np.linspace(0, np.pi, n)
    x = radius * np.outer(np.cos(u), np.sin(v)) + centre[0]
    y = radius * np.outer(np.sin(u), np.sin(v)) + centre[1]
    z = radius * np.outer(np.ones_like(u), np.cos(v)) + centre[2]
    return x, y, z

# -- _plot_completeness_error: returns None, draws mean abs radius error % (circles, left axis) and mean centre error nm (triangles, right axis) vs completeness, one colour per method, onto `ax`
def _plot_completeness_error(ax, error_summary: pd.DataFrame, cloud_types: list[str]) -> None:
    '''
    Twin-axis completeness-vs-error plot for one or more cloud types sharing an axes
    '''
    ax2 = ax.twinx()
    for i, cloud_type in enumerate(cloud_types):
        linestyle = '-' if i == 0 else '--'
        subset = error_summary[error_summary['cloud_type'] == cloud_type]
        for method, colour in METHOD_COLOURS.items():
            rows = subset[subset['method'] == method].sort_values('completeness_deg')
            if rows.empty:
                continue
            suffix = f' ({CLOUD_TYPE_LABELS[cloud_type]})' if len(cloud_types) > 1 else ''
            ax.plot(
                rows['completeness_deg'], rows['mean_abs_radius_error_pct'],
                marker='o', linestyle=linestyle, color=colour,
                label=f'{method} radius err %{suffix}',
            )
            ax2.plot(
                rows['completeness_deg'], rows['mean_centre_error_nm'],
                marker='^', linestyle=linestyle, color=colour, alpha=0.6,
                label=f'{method} centre err nm{suffix}',
            )
    ax.set_xlabel('Completeness (deg)')
    ax.set_ylabel('Mean abs radius error (%)')
    ax2.set_ylabel('Mean centre error (nm)')
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=6, loc='best')

# -- plot_diagram: returns None, saves the single benchmark diagram (one row per example cloud, 4 panels each: raw cloud / naive bounding box fit / isotropy-aware bounding box / completeness-vs-error)
def plot_diagram(
    examples: list[dict],
    error_summary: pd.DataFrame,
    out_path: str = 'benchmark_geometric_proxy.png',
    horizontal: bool = False,
) -> None:
    '''
    Grid is 3 examples x 4 panels; `horizontal` transposes it to 4 rows x 3 columns.
    Panels: raw point cloud, raw bbox proxy fit, cap-aware proxy fit (both overlaid on the true sphere for comparison), and the completeness-vs-error plot for that example's sweep(s)
    '''
    n_examples = len(examples)
    n_panels = 4
    n_rows, n_cols = (n_panels, n_examples) if horizontal else (n_examples, n_panels)
    fig = plt.figure(figsize=(5.2 * n_cols, 5.0 * n_rows))
    def subplot_index(panel_idx: int, example_idx: int) -> int:
        row, col = (panel_idx, example_idx) if horizontal else (example_idx, panel_idx)
        return row * n_cols + col + 1
    for example_idx, example in enumerate(examples):
        for panel_idx, kind in enumerate(['cloud', 'bbox', 'proxy', 'error']):
            projection = None if kind == 'error' else '3d'
            ax = fig.add_subplot(n_rows, n_cols, subplot_index(panel_idx, example_idx), projection=projection)
            if kind == 'cloud':
                ax.scatter(*example['points'].T, s=4, color='0.5', alpha=0.6)
                ax.set_title(f'{example["label"]}\nraw point cloud', fontsize=9)
            elif kind in ('bbox', 'proxy'):
                is_bbox = kind == 'bbox'
                name = 'naive bounding box' if is_bbox else 'isotropy-aware bounding box'
                centre = example['old_centre'] if is_bbox else example['new_centre']
                radius = example['old_radius'] if is_bbox else example['new_radius']
                colour = METHOD_COLOURS[name]
                ax.scatter(*example['points'].T, s=4, color='0.5', alpha=0.4)
                tx, ty, tz = _sphere_wireframe(np.asarray(example['true_centre']), example['true_radius'])
                ax.plot_wireframe(tx, ty, tz, color='black', linewidth=0.4, alpha=0.4)
                x, y, z = _sphere_wireframe(np.asarray(centre), radius)
                ax.plot_wireframe(x, y, z, color=colour, linewidth=0.6, alpha=0.6)
                ax.scatter(*centre, color=colour, marker='x', s=60)
                ax.set_title(f'{name}\nr={radius:.2f} (true {example["true_radius"]:.2f})', fontsize=9)
            else:
                _plot_completeness_error(ax, error_summary, example['sweep_cloud_types'])
                ax.set_title('Completeness vs error', fontsize=9)
    fig.suptitle('EValuator geometric proxy benchmark: naive bounding box vs isotropy-aware bounding box', fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)
