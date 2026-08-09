'''
=======================================
EValuator: BENCHMARKING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer

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
def benchmark_missing_wedge():
    '''
    Run missing-wedge correction/fitting accuracy benchmark
    '''
    print('Not yet implemented.')
    raise NotImplementedError()