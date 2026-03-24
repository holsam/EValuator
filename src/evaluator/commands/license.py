'''
=======================================
EValuator: PRINT LICENSE
=======================================
'''
# ====================
# Import external dependencies
# ====================
import typer
from rich import print

# ====================
# Initialise typer as evaluatorLicense
# ====================
evaluatorLicense = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False,
    # Disable --help option in terminal
    add_help_option=False
)

# ====================
# Define command: license
# ====================
@evaluatorLicense.command(rich_help_panel="Utility Commands")
def license():
    '''
    Print EValuator license to terminal and exit.
    '''
    with open('./LICENSE', 'r') as licensefile:
        print(f"\n{licensefile.read()}")
    typer.Exit(0)
