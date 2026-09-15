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
from evaluator.commands.tools.diagram import evaluatorDiagram
from evaluator.commands.tools.r_deps import evaluatorRDeps

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
evaluatorTools.add_typer(
    evaluatorDiagram,
    name='diagram',
    help='Generate diagrams',
)
evaluatorTools.add_typer(
    evaluatorRDeps,
    name='r-deps',
    help='Manage EValuator\'s R dependencies'
)