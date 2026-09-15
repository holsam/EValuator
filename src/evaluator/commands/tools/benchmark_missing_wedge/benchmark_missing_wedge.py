'''
=======================================
EValuator: MISSING WEDGE BENCHMARKING SCRIPT
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np, pandas as pd, time
from rich import print

# ====================
# Import internal utilities
# ====================
from evaluator.commands.tools.benchmark_missing_wedge import defaults
from evaluator.commands.tools.benchmark_missing_wedge import methods
from evaluator.commands.tools.benchmark_missing_wedge import summaries
from evaluator.commands.tools.utils import console
from evaluator.commands.tools.utils import synthetic

# ====================
# Define benchmarking logic
# ====================
# -- calculate_benchmark: returns DataFrame containing calculated diameters with mitigations applied
def calculate_benchmark(
    diameters_nm: tuple[float, ...],
    n_replicates: int,
    voxel_size_nm: float,
    tilt_range_deg: float,
    diameter_jitter_pct: float,
    shape_jitter: float,
    seed: int,
) -> pd.DataFrame:
    '''
    Run benchmark with realistic per-replicate variation, timing each mitigation
    '''
    # Seed random number generation
    rng = np.random.default_rng(seed)
    # Calculate total number of benchmarking points (subtract one so progress bar completes)
    total_points = (len(diameters_nm) * n_replicates) - 1
    point_index = 0
    rows = []
    # Loop through each diameter
    for nominal_d in diameters_nm:
        # Loop through each replicate
        for rep in range(n_replicates):
            # Per-replicate variation
            d = float(rng.normal(nominal_d, nominal_d * diameter_jitter_pct / 100))
            offset = tuple(rng.uniform(-0.5, 0.5, size=3))
            axes = tuple(rng.normal(1.0, shape_jitter, size=3))
            # Generate synthetic EVs across specified diameter range
            shell, truth = synthetic.generate_ev_shell(diameter_nm=d, voxel_size_nm=voxel_size_nm, centre_offset_voxels=offset, axis_ratios=axes)
            true_diameter = truth['diameter_nm']
            # Apply fourier missing wedge degradation
            degraded = synthetic.apply_fourier_missing_wedge(shell, tilt_range_deg=tilt_range_deg)

            # Baseline (no mitigation)
            t0 = time.perf_counter()
            baseline_d = methods._shell_voxel_diameter(degraded, voxel_size_nm)
            baseline_time = time.perf_counter() - t0

            # Apply mitigation 1: anisotropic closing → shell-volume diameter
            t0 = time.perf_counter()
            closed = methods.anisotropic_closing_per_component(degraded, z_radius=5, xy_radius=2)
            closed_d = methods._shell_voxel_diameter(closed, voxel_size_nm)
            closed_time = time.perf_counter() - t0

            # Apply mitigation 2: sphere fit on raw degraded shell
            t0 = time.perf_counter()
            points = np.argwhere(degraded) * voxel_size_nm
            if len(points) >= 50:
                _, fit_radius, fit_rmse = methods.fit_least_squares(points)
                fit_d = 2 * fit_radius
            else:
                fit_d = float('nan')
                fit_rmse = float('nan')
            fit_time = time.perf_counter() - t0

            # Apply mitigation 3: convex hull outer diameter
            t0 = time.perf_counter()
            hull_d = methods.hull_outer_diameter(shell, voxel_size_nm)
            hull_time = time.perf_counter() - t0

            # Apply mitigation 4: XY/Z diagnostic
            t0 = time.perf_counter()
            xyz = methods.xy_z_diameter_metrics(degraded, voxel_size_nm)
            xy_time = time.perf_counter() - t0

            # Apply mitigation 5: orientation score (not a diameter-recovery method, kept for diagnostics only)
            orient = methods.orientation_quality_score(degraded)

            # Add all results to DataFrame
            rows.append({
                'true_diameter_nm': true_diameter,
                'replicate': rep,
                'baseline_d_nm': baseline_d,
                'baseline_time_s': baseline_time,
                'closed_d_nm': closed_d,
                'closed_time_s': closed_time,
                'fit_d_nm': fit_d,
                'fit_rmse_nm': fit_rmse,
                'fit_time_s': fit_time,
                'hull_d_nm': hull_d,
                'hull_time_s': hull_time,
                'xy_d_nm': xyz['xy_diameter_nm'],
                'z_extent_nm': xyz['z_extent_nm'],
                'xy_z_ratio': xyz['xy_z_ratio'],
                'xy_time_s': xy_time,
                'orientation_score': orient['score'],
                'anisotropy': orient['anisotropy'],
            })
            # Increment point index and progress bar
            point_index += 1
            console.progress_bar(point_index, total_points)
    # Return dataframe  
    return pd.DataFrame(rows)

# -- calculate_errors: returns DataFrame of calculates 
def calculate_errors(df: pd.DataFrame) -> pd.DataFrame:
    err_df = df.copy()
    for name, (col, _) in defaults.METHODS.items():
        err = df[col] - df['true_diameter_nm']
        rel = err / df['true_diameter_nm']
        err_df.insert(loc=len(df.columns), column=f'{name}_error', value=err)
        err_df.insert(loc=len(df.columns), column=f'{name}_relative_error', value=rel)
    return err_df

# ====================
# Define script entrypoint
# ====================
def run_benchmark(
    output_dir: Path,
    diameters_nm: tuple[float, ...],
    n_replicates: int,
    voxel_size_nm: float,
    tilt_range_deg: float,
    diameter_jitter_pct: float,
    shape_jitter: float,
    seed: int,
):
    # Get passed parameters
    params = locals()
    # Print header and parameters
    console.print_header('benchmark', 'missing-wedge')
    console.print_benchmark_parameters(params)
    # Run benchmarking
    df = calculate_benchmark(diameters_nm, n_replicates, voxel_size_nm, tilt_range_deg, diameter_jitter_pct, shape_jitter, seed)
    df_err = calculate_errors(df)
    error_summary = summaries.summarise_errors(df)
    speed_summary = summaries.summarise_speed(df)
    # Define output paths
    df_out_path = output_dir / 'benchmark_missing_wedge_raw.csv'
    df_err_out_path = output_dir / 'benchmark_missing_wedge_err.csv'
    error_summary_out_path = output_dir / 'benchmark_missing_wedge_error_summary.csv'
    speed_summary_out_path = output_dir / 'benchmark_missing_wedge_speed_summary.csv'
    plot_out_path = output_dir / 'benchmark_missing_wedge.png'
    # Save results & plot
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(df_out_path, index=False)
    df_err.to_csv(df_err_out_path, index=False)
    error_summary.to_csv(error_summary_out_path, index=False)
    speed_summary.to_csv(speed_summary_out_path, index=False)
    summaries.plot_recovery_and_speed(df, speed_summary, error_summary, out_path=plot_out_path)
    # Print result file paths to terminal
    console.print_saved_file('Raw values saved to', df_out_path)
    console.print_saved_file('Error values saved to', df_err_out_path)
    console.print_saved_file('Error summary saved to', error_summary_out_path)
    console.print_saved_file('Speed summary saved to', speed_summary_out_path)
    console.print_saved_file('Plot saved to', plot_out_path)
    console.print_divider()
    print('\n')
