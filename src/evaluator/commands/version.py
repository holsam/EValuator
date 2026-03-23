import tomllib, typer
from rich import print

evaluatorVersion = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False,
    # Disable --help option in terminal
    add_help_option=False
)

@evaluatorVersion.command(rich_help_panel="Utility Commands")
def version():
    '''
    Print current EValuator version to terminal and exit.
    '''
    with open('pyproject.toml', 'rb') as f:
       contents = tomllib.load(f)
    print(f"\nRunning EValuator version: v{contents['project']['version']}\n")
    typer.Exit(0)
