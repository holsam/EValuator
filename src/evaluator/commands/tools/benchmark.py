'''
=======================================
EValuator: BENCHMARKING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer
from pathlib import Path
from typing import Annotated, Optional

# ====================
# Import benchmarking script and defaults
# ====================
from evaluator.commands.tools.benchmark_missing_wedge import benchmark_missing_wedge, defaults
from evaluator.commands.tools.benchmark_geometric_proxy import benchmark_geometric_proxy, defaults as geometric_defaults

# ====================
# Initialise typer as evaluatorAnimate
# ====================
evaluatorBenchmark = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Define command: animate
# ====================
@evaluatorBenchmark.command('missing-wedge')
def benchmark_mw(
    output_dir: Annotated[
        Path,
        typer.Option('-o', '--output-dir', help='Output directory for benchmark results', show_default=False)
    ] = Path('./out/benchmark'),
    min_diameter_nm: Annotated[
        int,
        typer.Option('--min-diameter', help='Minimum diameter to benchmark against'),
    ] = defaults.MIN_DIAMETER,
    max_diameter_nm: Annotated[
        int,
        typer.Option('--max-diameter', help='Maximum diameter to benchmark against'),
    ] = defaults.MAX_DIAMETER,
    diameter_step_nm: Annotated[
        int,
        typer.Option('--diameter-step', help='Steps (in nm) for diameter range to benchmark against'),
    ] = defaults.DIAMETER_STEP,
    n_replicates: Annotated[
        int,
        typer.Option('--n-replicates', help='Number of replicates per nominal diameter'),
    ] = defaults.REPLICATES,
    voxel_size_nm: Annotated[
        float,
        typer.Option('--voxel-size-nm', help='Voxel size to use for synthetic EVs'),
    ] = defaults.VOXEL_SIZE,
    tilt_range_deg: Annotated[
        float,
        typer.Option('--tilt-range', help='Tilt range to use for synthetic tilt series'),
    ] = defaults.TILT_RANGE,
    diameter_jitter_pct: Annotated[
        float,
        typer.Option('--diameter-jitter', help='Jitter to add for varying nominal diameter')
    ] = defaults.DIAMETER_JITTER,
    shape_jitter: Annotated[
        float,
        typer.Option('--shape-jitter', help='Jitter to add for varying EV shape')
    ] = defaults.SHAPE_JITTER,
    seed: Annotated[
        int,
        typer.Option('--seed', help='Seed to use for random generator')
    ] = defaults.SEED,
):
    '''
    Run missing-wedge correction/fitting accuracy benchmark
    '''
    benchmark_missing_wedge.run_benchmark(
        output_dir=output_dir,
        diameters_nm=range(min_diameter_nm, max_diameter_nm, diameter_step_nm),
        n_replicates=n_replicates,
        voxel_size_nm=voxel_size_nm,
        tilt_range_deg=tilt_range_deg,
        diameter_jitter_pct=diameter_jitter_pct,
        shape_jitter=shape_jitter,
        seed=seed,
    )

# ====================
# Define command: geometric-proxy
# ====================
@evaluatorBenchmark.command('geometric-proxy')
def benchmark_geometric(
    output_dir: Annotated[
        Path,
        typer.Option('-o', '--output-dir', help='Output directory for benchmark results', show_default=False)
    ] = Path('./out/benchmark'),
    min_cap_angle: Annotated[
        int,
        typer.Option('--min-cap-angle', help='Minimum polar-cap half-angle (deg) to benchmark against'),
    ] = geometric_defaults.MIN_CAP_ANGLE,
    max_cap_angle: Annotated[
        int,
        typer.Option('--max-cap-angle', help='Maximum polar-cap half-angle (deg) to benchmark against'),
    ] = geometric_defaults.MAX_CAP_ANGLE,
    cap_angle_step: Annotated[
        int,
        typer.Option('--cap-angle-step', help='Steps (deg) for polar-cap half-angle range to benchmark against'),
    ] = geometric_defaults.CAP_ANGLE_STEP,
    min_band_width: Annotated[
        int,
        typer.Option('--min-band-width', help='Minimum equatorial-band half-width (deg) to benchmark against'),
    ] = geometric_defaults.MIN_BAND_WIDTH,
    max_band_width: Annotated[
        int,
        typer.Option('--max-band-width', help='Maximum equatorial-band half-width (deg) to benchmark against'),
    ] = geometric_defaults.MAX_BAND_WIDTH,
    band_width_step: Annotated[
        int,
        typer.Option('--band-width-step', help='Steps (deg) for equatorial-band half-width range to benchmark against'),
    ] = geometric_defaults.BAND_WIDTH_STEP,
    n_replicates: Annotated[
        int,
        typer.Option('--n-replicates', help='Number of replicates per completeness value'),
    ] = geometric_defaults.REPLICATES,
    radius_nm: Annotated[
        float,
        typer.Option('--radius-nm', help='True sphere radius to use for synthetic point clouds'),
    ] = geometric_defaults.RADIUS,
    n_points: Annotated[
        int,
        typer.Option('--n-points', help='Number of points to sample per synthetic point cloud'),
    ] = geometric_defaults.N_POINTS,
    seed: Annotated[
        int,
        typer.Option('--seed', help='Seed to use for random generator')
    ] = geometric_defaults.SEED,
    horizontal: Annotated[
        bool,
        typer.Option('--horizontal', help='Transpose the diagram to 4 rows x 3 columns instead of 3 rows x 4 columns'),
    ] = False,
):
    '''
    Run geometric-proxy (estimateCentroidRadius) accuracy benchmark: naive bounding box proxy vs isotropy-aware bounding box proxy across partial spherical caps and equatorial bands
    '''
    benchmark_geometric_proxy.run_benchmark(
        output_dir=output_dir,
        cap_angles_deg=range(min_cap_angle, max_cap_angle + 1, cap_angle_step),
        band_widths_deg=range(min_band_width, max_band_width + 1, band_width_step),
        n_replicates=n_replicates,
        radius_nm=radius_nm,
        n_points=n_points,
        seed=seed,
        horizontal=horizontal,
    )