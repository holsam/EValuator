'''
=======================================
EValuator: GEOMETRIC PROXY BENCHMARKING SCRIPT
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np, pandas as pd, time
from pathlib import Path
from rich import print

# ====================
# Import internal utilities
# ====================
from evaluator.commands.tools.benchmark_geometric_proxy import defaults, methods, summaries
from evaluator.commands.tools.utils import console, synthetic
from evaluator.commands.label.utils.geometric_proxies import estimateCentroidRadius

# ====================
# Define benchmarking logic
# ====================
# -- calculate_benchmark: returns DataFrame of true vs recovered radius/centre for both methods, across cloud types and completeness
def calculate_benchmark(
    cap_angles_deg: range,
    band_widths_deg: range,
    n_replicates: int,
    radius_nm: float,
    n_points: int,
    seed: int,
) -> pd.DataFrame:
    '''
    Sweep polar-cap and equatorial-band completeness, timing/error-checking both proxy methods against each other on realistic partial point clouds
    '''
    rng = np.random.default_rng(seed)
    sweeps = (
        [('polar_cap', angle) for angle in cap_angles_deg]
        + [('equatorial_band', width) for width in band_widths_deg]
    )
    total_points = (len(sweeps) * n_replicates) - 1
    point_index = 0
    rows = []
    for cloud_type, completeness_deg in sweeps:
        for rep in range(n_replicates):
            centre = tuple(rng.uniform(-1.0, 1.0, size=3))
            pole = rng.normal(size=3)
            rep_seed = int(rng.integers(0, 2 ** 31))
            if cloud_type == 'polar_cap':
                points, truth = synthetic.generate_spherical_cap_points(
                    radius_nm=radius_nm, half_angle_deg=completeness_deg,
                    centre=centre, pole=pole, n=n_points, seed=rep_seed,
                )
            else:
                points, truth = synthetic.generate_equatorial_band_points(
                    radius_nm=radius_nm, band_half_width_deg=completeness_deg,
                    centre=centre, pole=pole, n=n_points, seed=rep_seed,
                )
            true_centre = truth['centre']
            t0 = time.perf_counter()
            old_centre, old_radius = methods.bbox_centroid_radius(points)
            old_time = time.perf_counter() - t0
            t0 = time.perf_counter()
            new_centre, new_radius = estimateCentroidRadius(points)
            new_time = time.perf_counter() - t0
            rows.append({
                'cloud_type': cloud_type,
                'completeness_deg': completeness_deg,
                'replicate': rep,
                'true_radius_nm': radius_nm,
                'old_radius_nm': old_radius,
                'old_centre_error_nm': float(np.linalg.norm(old_centre - true_centre)),
                'old_time_s': old_time,
                'new_radius_nm': new_radius,
                'new_centre_error_nm': float(np.linalg.norm(new_centre - true_centre)),
                'new_time_s': new_time,
            })
            point_index += 1
            console.progress_bar(point_index, total_points)
    return pd.DataFrame(rows)

# -- collect_example_clouds: returns the 3 representative point clouds shown in the diagram (full sphere, most-concentrated cap, most-concentrated band)
def collect_example_clouds(
    cap_angles_deg: range,
    band_widths_deg: range,
    radius_nm: float,
    n_points: int,
    seed: int,
) -> list[dict]:
    '''
    One example per diagram row: a full sphere (anchor case, relevant to both sweeps), the
    smallest (most concentrated) polar cap, and the smallest (most concentrated) equatorial
    band — the two extremes `estimateCentroidRadius` is specifically written to handle
    '''
    specs = [
        ('Full sphere', 'full', None, ['polar_cap', 'equatorial_band']),
        ('Concentrated polar cap', 'polar_cap', min(cap_angles_deg), ['polar_cap']),
        ('Concentrated equatorial band', 'equatorial_band', min(band_widths_deg), ['equatorial_band']),
    ]
    examples = []
    for label, generator, completeness_deg, sweep_cloud_types in specs:
        if generator == 'full':
            points, truth = synthetic.generate_full_sphere_points(
                radius_nm=radius_nm, centre=(0.0, 0.0, 0.0), n=n_points, seed=seed,
            )
        elif generator == 'polar_cap':
            points, truth = synthetic.generate_spherical_cap_points(
                radius_nm=radius_nm, half_angle_deg=completeness_deg,
                centre=(0.0, 0.0, 0.0), pole=(0.0, 0.0, 1.0), n=n_points, seed=seed,
            )
        else:
            points, truth = synthetic.generate_equatorial_band_points(
                radius_nm=radius_nm, band_half_width_deg=completeness_deg,
                centre=(0.0, 0.0, 0.0), pole=(0.0, 0.0, 1.0), n=n_points, seed=seed,
            )
        old_centre, old_radius = methods.bbox_centroid_radius(points)
        new_centre, new_radius = estimateCentroidRadius(points)
        examples.append({
            'label': label,
            'sweep_cloud_types': sweep_cloud_types,
            'points': points,
            'true_centre': truth['centre'],
            'true_radius': radius_nm,
            'old_centre': old_centre,
            'old_radius': old_radius,
            'new_centre': new_centre,
            'new_radius': new_radius,
        })
    return examples

# ====================
# Define script entrypoint
# ====================
def run_benchmark(
    output_dir: Path,
    cap_angles_deg: range,
    band_widths_deg: range,
    n_replicates: int,
    radius_nm: float,
    n_points: int,
    seed: int,
    horizontal: bool = False,
):
    params = locals()
    console.print_header('benchmark', 'geometric-proxy')
    console.print_benchmark_parameters(params)
    df = calculate_benchmark(cap_angles_deg, band_widths_deg, n_replicates, radius_nm, n_points, seed)
    error_summary = summaries.summarise_errors(df)
    df_out_path = output_dir / 'benchmark_geometric_proxy_raw.csv'
    error_summary_out_path = output_dir / 'benchmark_geometric_proxy_error_summary.csv'
    plot_out_path = output_dir / 'benchmark_geometric_proxy.png'
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(df_out_path, index=False)
    error_summary.to_csv(error_summary_out_path, index=False)
    examples = collect_example_clouds(cap_angles_deg, band_widths_deg, radius_nm, n_points, seed)
    summaries.plot_diagram(examples, error_summary, out_path=plot_out_path, horizontal=horizontal)
    console.print_saved_file('Raw values saved to', df_out_path)
    console.print_saved_file('Error summary saved to', error_summary_out_path)
    console.print_saved_file('Diagram saved to', plot_out_path)
    console.print_divider()
    print('\n')
