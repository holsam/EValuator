'''
CLI command: config
'''

# -- Import external dependencies ----------------
import typer
from typing import Annotated

# -- Import internal EValuator functions and variables
import evaluator.commands.config as configFuncs

# -- Initialiate Typer class for config command --
evaluatorConfig = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False,
    # Run callback even if no subcommand is given
    invoke_without_command=True
)

# -- Define config Typer callback ----------------
@evaluatorConfig.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    # If a subcommand was entered
    if ctx.invoked_subcommand is not None:
        # Don't return anything
        return
    else:
        configFuncs.config_exists()

# -- Define config init subcommand ---------------
@evaluatorConfig.command(rich_help_panel="Config Commands")
def init():
    '''
    Create a user config file populated with default settings in the OS config directory.
    '''
    configFuncs.config_init()

# -- Define config exists subcommand -------------
@evaluatorConfig.command(rich_help_panel='Config Commands')
def exists() -> None:
    configFuncs.config_exists()

# -- Define config list subcommand ---------------
@evaluatorConfig.command(rich_help_panel='Config Commands')
def list() -> None:
    '''
    Print the current config values, highlighting any user values which differ from EValuator defaults.
    '''
    configFuncs.config_list()

# -- Define config verify subcommand -------------
@evaluatorConfig.command(rich_help_panel="Config Commands")
def verify() -> None:
    '''
    Verifies that all expected keys are present in the current user config file by checking against the bundled default config file. Exits with non-zero code if missing or unexpected keys are found.
    '''
    configFuncs.config_verify()

# -- Define config reset subcommand --------------
@evaluatorConfig.command(rich_help_panel="Config Commands")
def reset(
    force: Annotated[
        bool,
        typer.Option('--force', help='Skip confirmation prompt and immediately overwrite config.toml file.'),
    ] = False) -> None:
    '''
    Overwrites the users config file with EValuator's built-in default values.
    Includes a confirmation prompt unless --force supplied.
    '''
    configFuncs.config_reset(f=force)