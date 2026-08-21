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