'''
=======================================
EValuator: PRINT VERSION
=======================================
'''
# ====================
# Import external dependencies
# ====================
import tomllib, typer
from importlib.resources import files as pkg_files
from rich import print

# ====================
# Import internal dependencies
# ====================
import evaluator.commands.version as versionFuncs

# ====================
# Initialise typer as evaluatorVersion
# ====================
evaluatorVersion = typer.Typer(
    add_completion=False,
    add_help_option=False,
)

# ====================
# Define command: version
# ====================
@evaluatorVersion.command(rich_help_panel="Utility Commands")
def version():
    '''
    Print current EValuator version to terminal and exit.
    '''
    versionFuncs.printVersion()