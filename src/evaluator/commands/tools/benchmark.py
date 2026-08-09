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
def benchmark_missing_wedge(
    input_dir: Annotated[
        Optional[Path],
        typer.Option('-i', '--input-dir', help='Directory to use during benchmarking')
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option('-o', '--output-dir', help='Output directory for benchmark results', show_default=False)
    ] = Path('./out/benchmark'),
):
    '''
    Run missing-wedge correction/fitting accuracy benchmark
    '''
    print('Not yet implemented.')
    raise NotImplementedError()