'''
=======================================
EValuator: MISSING WEDGE BENCHMARKING SCRIPT SUMMARY FUNCTIONS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import matplotlib.pyplot as plt, numpy as np, pandas as pd

# ====================
# Import internal utilities
# ====================
from evaluator.commands.tools.benchmark_missing_wedge import defaults

# ====================
# Define summary functions
# ====================
# -- summarise_errors: returns DataFrame of per-method error statistics
def summarise_errors(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Compute per-method error statistics, pooling across diameters
    '''
    rows = []
    for name, (col, _) in defaults.METHODS.items():
        err = df[col] - df['true_diameter_nm']
        rel = err / df['true_diameter_nm']
        rows.append({
            'method': name,
            'mean_signed_error_nm': float(err.mean()),
            'rmse_nm': float(np.sqrt((err ** 2).mean())),
            'mean_abs_rel_error_pct': float(100 * rel.abs().mean()),
            'max_abs_error_nm': float(err.abs().max()),
        })
    return pd.DataFrame(rows)

# -- summarise_speed: returns DataFrame of per-method runtime statistics
def summarise_speed(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Compute per-method runtime statistics (milliseconds), pooling across diameters
    '''
    rows = []
    for name, (_, time_col) in defaults.METHODS.items():
        t_ms = df[time_col] * 1000
        rows.append({
            'method': name,
            'mean_time_ms': float(t_ms.mean()),
            'median_time_ms': float(t_ms.median()),
        })
    return pd.DataFrame(rows)

# -- plot_recovery_and_speed: returns None, saves a two-panel figure for accuracy/speed
def plot_recovery_and_speed(
    df: pd.DataFrame,
    speed_summary: pd.DataFrame,
    error_summary: pd.DataFrame,
    out_path: str = 'benchmark_missing_wedge.png',
) -> None:
    '''
    Build a two-panel figure:
      left  - recovered vs actual diameter, all methods, with per-method linear fits
      right - mean runtime vs mean abs % error, one point per method (log-scale x)
    '''
    fig, (ax_recovery, ax_speed) = plt.subplots(1, 2, figsize=(13, 5.5))

    colours = plt.cm.tab10(np.linspace(0, 1, len(defaults.METHODS)))
    true_d = df['true_diameter_nm'].to_numpy()
    lims = [true_d.min() * 0.95, true_d.max() * 1.05]

    # -- Left panel: recovery scatter + linear fits
    for (name, (col, _)), colour in zip(defaults.METHODS.items(), colours):
        recovered = df[col].to_numpy()
        mask = ~np.isnan(recovered)
        x, y = true_d[mask], recovered[mask]
        ax_recovery.scatter(x, y, s=8, alpha=0.25, color=colour, label=None)
        if mask.sum() > 1:
            slope, intercept = np.polyfit(x, y, 1)
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float('nan')
            x_line = np.array(lims)
            ax_recovery.plot(
                x_line, slope * x_line + intercept, color=colour, linewidth=2,
                label=f'{name} (slope={slope:.2f}, R\u00b2={r2:.2f})',
            )

    ax_recovery.plot(lims, lims, 'k--', linewidth=1, label='Identity (perfect recovery)')
    ax_recovery.set_xlim(lims)
    ax_recovery.set_ylim(lims)
    ax_recovery.set_xlabel('True diameter (nm)')
    ax_recovery.set_ylabel('Recovered diameter (nm)')
    ax_recovery.set_title('Recovered vs actual diameter')
    ax_recovery.legend(fontsize=7, loc='upper left')

    # -- Right panel: speed vs accuracy trade-off
    merged = speed_summary.merge(error_summary, on='method')
    for _, row in merged.iterrows():
        ax_speed.scatter(row['mean_time_ms'], row['mean_abs_rel_error_pct'], s=80)
        ax_speed.annotate(
            row['method'], (row['mean_time_ms'], row['mean_abs_rel_error_pct']),
            textcoords='offset points', xytext=(6, 4), fontsize=8,
        )
    ax_speed.set_xscale('log')
    ax_speed.set_xlabel('Mean runtime per vesicle (ms, log scale)')
    ax_speed.set_ylabel('Mean absolute error (%)')
    ax_speed.set_title('Accuracy vs computational cost')

    fig.suptitle('EValuator missing-wedge mitigation benchmark', fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
