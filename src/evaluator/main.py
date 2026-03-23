# ====================
# Import package dependencies
# ====================
import logging, tomllib, typer
from typing import Annotated
from rich import print

# ====================
# Load default configuration from config.toml
# ==================== 
with open('./src/evaluator/config.toml', 'rb') as configfile:
    config = tomllib.load(configfile)

# =========================
# INITIALISE LOGGER
# =========================
lg = logging.getLogger("__name__")


# ====================
# Import EValuator commands and utility functions
# ====================
from .utils import initEvaluator
from .commands.analyse import evaluatorAnalyse
from .commands.label import evaluatorLabel
from .commands.license import evaluatorLicense
from .commands.version import evaluatorVersion
from .commands.visualise import evaluatorVisualise

# ====================
# Print top splash EValuator commands and utility functions
# ====================
initEvaluator()

# ====================
# Initialise typer as evaluator
# ====================
evaluator = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False,
    # Enable using markdown syntax in docstrings and help text
    rich_markup_mode="rich",
    # If no command used, show help text instead of error
    no_args_is_help=True,
)
# ====================
# Add command-specific typers to evaluator typer
# nb order of add is important within groups as determines order that they'll be shown
# ====================
evaluator.add_typer(evaluatorAnalyse)
evaluator.add_typer(evaluatorLabel)
evaluator.add_typer(evaluatorVisualise)
evaluator.add_typer(evaluatorLicense)
evaluator.add_typer(evaluatorVersion)

# ====================
# Define callback to use for main evaluator typer if called (e.g. with evaluator --help)
# ====================
@evaluator.callback()
def main(
    # Define argument debug: is an optional boolean and defaults to False 
    debug: Annotated[
        bool,
        typer.Option("-vv", "--debug", help="Show debug messages in terminal (implies --verbose).", rich_help_panel="Options")
    ] = False,
    # Define argument verbose: is an optional boolean and defaults to False 
    verbose: Annotated[
        bool,
        typer.Option("-v","--verbose", help="Show progress in terminal.", rich_help_panel="Options")
    ] = False,
):
    # Check if debug flag was provided, and if set logging level to debug
    if debug:
        log_level = logging.DEBUG
    # Check if verbose flag was provided, and if so set logging level to information
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(format='%(asctime)s %(levelname)-10s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level = log_level)