'''
=======================================
EValuator: APPLICATION ENTRY POINT
=======================================
Wires all command typers to the root evaluator typer and defines the top-level callback (--verbose / --debug flags).
'''

# ====================
# Import external dependencies
# ====================
import logging, typer
from typing import Annotated

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import configure_logging, initEvaluator, lg

# ====================
# Import EValuator commands
# ====================
from evaluator.commands.config.cli import evaluatorConfig
from evaluator.commands.analyse.cli import evaluatorAnalyse
from evaluator.commands.label.cli import evaluatorLabel
from evaluator.commands.license.cli import evaluatorLicense
from evaluator.commands.model.cli import evaluatorModel
from evaluator.commands.plot.cli import evaluatorPlot
from evaluator.commands.tools.cli import evaluatorTools
from evaluator.commands.version.cli import evaluatorVersion
from evaluator.commands.visualise.cli import evaluatorVisualise

# ====================
# Print startup splash
# ====================
initEvaluator()

# ====================
# Initialise root typer
# ====================
evaluator = typer.Typer(
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# ====================
# Register sub-typers
# nb. order of add_typer determines display order within each help panel
# ====================
evaluator.add_typer(
    evaluatorLabel,
)
evaluator.add_typer(
    evaluatorModel,
)
evaluator.add_typer(
    evaluatorAnalyse,
)
evaluator.add_typer(
    evaluatorPlot,
)
evaluator.add_typer(
    evaluatorVisualise,
    name='visualise',
    help='Generate visualisations from MRC data',
    rich_help_panel='Component Visualisation')
evaluator.add_typer(
    evaluatorConfig,
)
evaluator.add_typer(
    evaluatorLicense,
)
evaluator.add_typer(
    evaluatorTools,
    name='tools',
    help='Animation, benchmarking and miscellaneous tools',
    rich_help_panel='Utilities',
)
evaluator.add_typer(
    evaluatorVersion
)

# ====================
# Top-level callback: --verbose / --debug flags
# ====================
@evaluator.callback()
def main(
    debug: Annotated[
        bool,
        typer.Option("-vv", "--debug", help="Show debug messages in terminal (implies --verbose).", rich_help_panel="Options")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Show progress in terminal.", rich_help_panel="Options")
    ] = False,
):
    level = 'DEBUG' if debug else 'INFO' if verbose else 'WARNING'
    log_path = configure_logging(level)
    # Output confirmation message that logging has been set up
    lg.info(f'Log messages (levels: <yellow><b>warning</b></yellow>{', <b>info</b>, <blue><b>debug</b></blue>' if debug else ', info' if verbose else ''}) will be written to <cyan>{log_path}</cyan>')
