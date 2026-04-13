'''
=======================================
EValuator: APPLICATION ENTRY POINT
=======================================
Wires all command typers to the root evaluator typer and defines
the top-level callback (--verbose / --debug flags).
'''

# ====================
# Import external dependencies
# ====================
import logging, typer
from typing import Annotated

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import initEvaluator, lg

# ====================
# Import EValuator commands
# ====================
from evaluator.cli.config import evaluatorConfig
from evaluator.cli.analyse import evaluatorAnalyse
from evaluator.cli.label import evaluatorLabel
from evaluator.cli.license import evaluatorLicense
from evaluator.cli.version import evaluatorVersion
from evaluator.cli.visualise import evaluatorVisualise

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
    name='label',
    help='Label connected components in a segmentation MRC',
    rich_help_panel='Identification'
)
evaluator.add_typer(
    evaluatorAnalyse,
    name='analyse',
    help='Run morphological analysis pipeline on labelled MRC files',
    rich_help_panel='Commands'
)
evaluator.add_typer(
    evaluatorVisualise,
    name='visualise',
    help='Generate visualisations from MRC data',
    rich_help_panel='Commands')
evaluator.add_typer(
    evaluatorConfig,
    name='config',
    help='Manage EValuator configuration files',
    rich_help_panel='Utilities')
evaluator.add_typer(
    evaluatorLicense,
    name='license',
    help='Print EValuator license',
    rich_help_panel='Utilities')
evaluator.add_typer(
    evaluatorVersion,
    name='version',
    help='Print current EValuator version',
    rich_help_panel='Utilities')

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
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(
        format='%(asctime)s %(levelname)-10s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level,
    )