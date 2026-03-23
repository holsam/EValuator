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
    with open('./src/evaluator/version.toml', 'rb') as versionfile:
       version = tomllib.load(versionfile)
    print(f"\nRunning EValuator version: v{version['version']['version']}\n")
    typer.Exit(0)
