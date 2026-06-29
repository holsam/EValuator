'''
Benchmark the EValuator missing-wedge mitigations against a known ground truth

Workflow:
- Generates synthetic EVs across a range of true diameters
- Applies the Fourier missing-wedge degradation
- Runs each mitigation
- Reports recovered-diameter error vs ground truth
'''
# -- Import external dependencies
import os, numpy as np, pandas as pd, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from rich import print
from tqdm import tqdm

# -- Import internal functions
from evaluator.utils.missing_wedge import (
    anisotropic_closing_per_component,
    fit_sphere_least_squares,
    hull_outer_diameter,
    orientation_quality_score,
    xy_z_diameter_metrics,
)
from evaluator.utils.synthetic import (
    apply_polar_gaps,
    generate_ev_shell,
)

# -- Define internal constants
DIAMETERS = range(20,200,40)
REPLICATES = 8
VOXEL_SIZE = 1.36
TILT_RANGE = 60.0
DIAMETER_JITTER = 6.0
SHAPE_JITTER = 0.2
SEED = 0

# -- shell_voxel_diameter: returns float corresponding to raw shell voxel count
def shell_voxel_diameter(binary: np.ndarray, voxel_size_nm: float) -> float:
    '''
    Calculate equivalent diameter from raw shell voxel count
    '''
    n = int(binary.sum())
    if n == 0:
        return float('nan')
    return 2 * (3 * n * voxel_size_nm ** 3 / (4 * np.pi)) ** (1 / 3)

# -- _compute_replicate: returns a dictionary for a single replicate's row
def _compute_replicate(
    nominal_d: float,
    rep: int,
    seed_offset: int,
    voxel_size_nm: float,
    tilt_range_deg: float,
    diameter_jitter_pct: float,
    shape_jitter: float,
) -> dict:
    '''
    Standalone replicate computation for multiprocessing
    '''
    rng = np.random.default_rng(seed_offset + rep)
    gap_half_angle = 90.0 - tilt_range_deg
    d = float(rng.normal(nominal_d, nominal_d * diameter_jitter_pct / 100))
    offset = tuple(rng.uniform(-0.5, 0.5, size=3))
    axes = tuple(rng.normal(1.0, shape_jitter, size=3))
    shell, truth = generate_ev_shell(
        diameter_nm=d,
        voxel_size_nm=voxel_size_nm,
        centre_offset_voxels=offset,
        axis_ratios=axes,
    )
    true_diameter = truth['diameter_nm']
    degraded = apply_polar_gaps(shell, gap_half_angle_deg=gap_half_angle)
    baseline_d = shell_voxel_diameter(degraded, voxel_size_nm)
    closed = anisotropic_closing_per_component(degraded, z_radius=5, xy_radius=2)
    points = np.argwhere(degraded) * voxel_size_nm
    if len(points) >= 50:
        _, fit_radius, fit_rmse = fit_sphere_least_squares(points)
        fit_d = 2 * fit_radius
    else:
        fit_d = float('nan')
        fit_rmse = float('nan')
    hull_d = hull_outer_diameter(closed, voxel_size_nm)
    xyz = xy_z_diameter_metrics(degraded, voxel_size_nm)
    orient = orientation_quality_score(degraded)
    return {
        'nominal_diameter_nm': nominal_d,
        'true_diameter_nm': true_diameter,
        'replicate': rep,
        'baseline_d_nm': baseline_d,
        'fit_d_nm': fit_d,
        'fit_rmse_nm': fit_rmse,
        'hull_d_nm': hull_d,
        'xy_d_nm': xyz['xy_diameter_nm'],
        'z_extent_nm': xyz['z_extent_nm'],
        'xy_z_ratio': xyz['xy_z_ratio'],
        'orientation_score': orient['score'],
        'anisotropy': orient['anisotropy'],
    }

# -- run_benchmark: streams results to CSV incrementally, returns path
def run_benchmark(
    output_path: str = 'benchmark_missing_wedge_raw.csv',
    diameters_nm: tuple[float, ...] = DIAMETERS,
    n_replicates: int = REPLICATES,
    voxel_size_nm: float = VOXEL_SIZE,
    tilt_range_deg: float = TILT_RANGE,
    diameter_jitter_pct: float = DIAMETER_JITTER,
    shape_jitter: float = SHAPE_JITTER,
    seed: int = SEED,
    max_workers: int = 3,
) -> str:
    '''
    Run benchmark with per-diameter parallelisation, and incremental CSV streaming
    Streams results to CSV after each diameter block.
    '''
    header_written = False
    total_points = len(diameters_nm) * n_replicates
    with tqdm(total=total_points, desc='Benchmarking points generated') as pbar:
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            for nominal_d in diameters_nm:
                # Submit all replicates for this diameter to the pool
                futures = [
                    executor.submit(
                        _compute_replicate,
                        nominal_d=nominal_d,
                        rep=rep,
                        seed_offset=seed + int(nominal_d) * 1000,  # deterministic per diameter for reproducibility with parallelisation
                        voxel_size_nm=voxel_size_nm,
                        tilt_range_deg=tilt_range_deg,
                        diameter_jitter_pct=diameter_jitter_pct,
                        shape_jitter=shape_jitter,
                    )
                    for rep in range(n_replicates)
                ]
                # Collect results as they complete
                rows = []
                for future in futures:
                    row = future.result()
                    rows.append(row)
                    pbar.update(1)
                # Flush this diameter block to disk
                block = pd.DataFrame(rows)
                block.to_csv(output_path, mode='a', index=False, header=not header_written)
                header_written = True
                del rows, block
    return output_path

# -- summarise_errors: returns DataFrame of per-method error statistics
def summarise_errors(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Compute per-method error statistics, pooling across diameters
    '''
    methods = {
        'baseline': 'baseline_d_nm',
        'sphere fit': 'fit_d_nm',
        'convex hull': 'hull_d_nm',
        'XY-projection diameter': 'xy_d_nm',
    }
    rows = []
    for name, col in methods.items():
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

def calculate_errors(df: pd.DataFrame) -> pd.DataFrame:
    methods = {
        'baseline': 'baseline_d_nm',
        'sphere fit': 'fit_d_nm',
        'convex hull': 'hull_d_nm',
        'XY-projection diameter': 'xy_d_nm',
    }
    err_df = df.copy()
    for name, col in methods.items():
        err = df[col] - df['true_diameter_nm']
        rel = err / df['true_diameter_nm']
        err_df.insert(loc=len(df.columns), column=f'{name}_error', value=err)
        err_df.insert(loc=len(df.columns), column=f'{name}_relative_error', value=rel)
    return err_df

def print_termini(terminus: str):
    terminal_width = os.get_terminal_size().columns
    if terminus == "start":
        print(f'\n')
        print(f'{"="*int((terminal_width-20)/2)}', 'BEGIN BENCHMARKING',f'{"="*int((terminal_width-20)/2)}')
        print(
            f'Benchmarking parameters:\n'
            f'\t- True diameters: {DIAMETERS}\n'
            f'\t- Replicates per diameter: {REPLICATES}\n'
            f'\t- Voxel size (nm): {VOXEL_SIZE}\n'
            f'\t- Tilt range (°): {TILT_RANGE}\n'
            f'\t- Diameter jitter: {DIAMETER_JITTER}\n'
            f'\t- Shape jitter: {SHAPE_JITTER}\n'
            f'\t- RNG seed: {SEED}\n'
        )
    if terminus == "end":
        print(f'{"="*int((terminal_width-18)/2)}', 'END BENCHMARKING',f'{"="*int((terminal_width-18)/2)}')
        print(f'\n')

# -- Entrypoint
if __name__ == '__main__':
    print_termini('start')
    # Run benchmark
    raw_path = 'benchmark_missing_wedge_raw.csv'
    if not Path(raw_path).exists():
        run_benchmark(output_path=raw_path)
    # Read back from disk for summaries
    df = pd.read_csv(raw_path)
    df_err = calculate_errors(df)
    # Print results
    print(f'[bold]Per-EV results (head):[/bold]')
    print(df.head(10).to_string(index=False))
    print(f'[bold]Per-method error summary:[/bold]')
    print(summarise_errors(df).to_string(index=False))
    summarise_errors(df).to_csv('benchmark_missing_wedge_summary.csv', index=False)
    df_err.to_csv('benchmark_missing_wedge_err.csv', index=False)
    print_termini('end')