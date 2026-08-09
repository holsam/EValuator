'''
=======================================
EValuator: UTILITY TOOLS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer

# ====================
# Import tool subcommand Typer classes
# ====================
from evaluator.commands.tools.animate import evaluatorAnimate
from evaluator.commands.tools.benchmark import evaluatorBenchmark

# ====================
# Initialise typer as evaluatorTools
# ====================
evaluatorTools = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Add tool subcommand Typers
# ====================
evaluatorTools.add_typer(
    evaluatorAnimate,
    name='animate',
    help='Generate animations/visualisations',
)
evaluatorTools.add_typer(
    evaluatorBenchmark,
    name='benchmark',
    help='Run EValuator benchmarks'
)
