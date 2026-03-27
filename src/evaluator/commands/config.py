'''
=======================================
EValuator: CONFIGURATION MANAGEMENT
=======================================
'''
# ====================
# Import external dependencies
# ====================
import tomllib, tomli_w, typer
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir
from rich import print
from rich.console import Console
from rich.table import Table
from typing import Annotated

# ====================
# Import EValuator utility functions
# ====================
from ..utils import loadDefaultConfig, userConfigPath

# ====================
# Initialise typer as evaluatorConfig
# ====================
evaluatorConfig = typer.Typer(
    # Disable --install-completion and --show-completion options in terminal
    add_completion=False,
    # If no subcommand used, show help text instead of error
    # no_args_is_help=True,
    # Run callback even if no subcommand is given
    invoke_without_command=True
)

# ====================
# Define callback (runs when no subcommand used)
# ====================
@evaluatorConfig.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    # If a subcommand was entered
    if ctx.invoked_subcommand is not None:
        # Don't return anything
        return
    config_path = userConfigPath()
    default_config = flattenToml(loadDefaultConfig())
    if not config_path.exists():
        print(
            f'\n[bold yellow]No user config file found.[/bold yellow]\n'
            f'EValuator is using built-in default values.\n'
            f'\nTo create a user config file ([cyan]{config_path}[/cyan]) run:\n'
            f'  [bold]evaluator config init[/bold]\n'
            f'\nTo see available EValuator config commands run:\n'
            f'  [bold]evaluator config --help[/bold]\n'
        )
        return
    print(f'\n[bold green]User config file found:[/bold green] [cyan]{config_path}[/cyan]\n')
    try:
        user_config = flattenToml(loadUserConfig())
        printConfigTable(user_config, default_config)
        print(f'\nRun [bold]evaluator config list[/bold] for more information.\n\n')
    except tomllib.TOMLDecodeError as e:
        print(f'[bold red]ERROR:[/bold red] Could not parse config file: {e}.')
        raise typer.Exit(1)

# ====================
# Define subcommand: init
# ====================
@evaluatorConfig.command(rich_help_panel="Config Commands")
def init():
    '''
    Create a user config file populated with default settings in the OS config directory.
    '''
    print()
    # Get path to user config file
    config_path = userConfigPath()
    # Check if file already exists
    if not internalConfigCheck(config_path, exists=False):
        raise typer.Exit(1)
    try:
        # Load default config from bundled toml file
        defaults = loadDefaultConfig()
        # Write default config to user config file path
        writeUserConfig(defaults)
        # Print success message
        print(
            f'[bold green]SUCCESS:[/bold green] User config file written to [cyan]{config_path}[/cyan]\n'
        )
    except Exception as e:
        # Print error message
        print(
            f'[bold red]ERROR:[/bold red] Failed to write user config file to [cyan]{config_path}[/cyan]: {e}.\n'
        )
        raise typer.Exit(1)

# ====================
# Define subcommand: exists
# ====================
@evaluatorConfig.command(rich_help_panel='Config Commands')
def exists() -> None:
    '''
    Report whether a user config file exists and the expected file path.
    '''
    print()
    # Get path to user config file
    config_path = userConfigPath()
    # If file exists:
    if config_path.exists():
        # Print success message
        print(
            f"[bold green]SUCCESS:[/bold green]User config file found at [cyan]{config_path}[/cyan]\n"
        )
    else:
        # Otherwise, print warning
        print(f'[bold yellow]WARNING:[/bold yellow] No user config file found at [cyan]{config_path}[/cyan]\nRun [bold]evaluator config init[/bold] to create one.\n')
        raise typer.Exit(1)


# ====================
# Define subcommand: list
# ====================
@evaluatorConfig.command(rich_help_panel='Config Commands')
def list() -> None:
    '''
    Print the current config values, highlighting any user values which differ from EValuator defaults.
    '''
    # Get path to user config file
    config_path = userConfigPath()
    # Load default config
    try:
        default_config = flattenToml(loadDefaultConfig())
    except tomllib.TOMLDecodeError as e:
        # Print error
        print(
            f'[bold red]ERROR:[/bold red] Could not parse default config file: {e}.\n'
        )
        raise typer.Exit(1)
    # Check if user config file already exists
    if internalConfigCheck(config_path, exists=True):
        print(
            f'[bold blue]Current config settings:[/bold blue] user config file ([cyan]{config_path}[/cyan]).\n'
        )
        try:
            # Use user config files:
            user_config = loadUserConfig()
        except tomllib.TOMLDecodeError as e:
            # Print error
            print(
                f'[bold red]ERROR:[/bold red] Could not parse user config file: {e}.\n'
            )
            raise typer.Exit(1)
        current_config = flattenToml(user_config)
    else:
        print(f'[bold blue]Current config settings:[/bold blue] default config file.\n')
        current_config = default_config
    printConfigTable(current_config, default_config)
    print()

# ====================
# Define subcommand: verify
# ====================
@evaluatorConfig.command(rich_help_panel="Config Commands")
def verify() -> None:
    '''
    Verifies that all expected keys are present in the current user config file by checking against the bundled default config file. Exits with non-zero code if missing or unexpected keys are found.
    '''
    # Get path to user config file
    config_path = userConfigPath()
    # Check user config file exits
    if not internalConfigCheck(config_path, exists=True):
        raise typer.Exit(1)
    try:
        user_config = flattenToml(loadUserConfig())
        default_config = flattenToml(loadDefaultConfig())
    except tomllib.TOMLDecodeError as e:
        # Print error
        print(
            f'[bold red]ERROR:[/bold red] Could not parse config file: {e}.\n'
        )
        raise typer.Exit(1)
    missing = [k for k in default_config if k not in user_config]
    unexpected = [k for k in user_config if k not in default_config]
    issues = missing or unexpected
    if not issues:
        print(
            f'[bold green]SUCCESS:[/bold green] User config file ([cyan]{config_path}[/cyan]) is valid.\n'
        )
        return
    if missing:
        print(
            f'[bold red]ERROR:[/bold red] Found {len(missing)} missing keys in user config file ([cyan]{config_path}[/cyan]):'
        )
        for k in sorted(missing):
            print(
                f'\t[red]✗[/red] {k} [dim](expected: {default_config[k]})[/dim]'
            )
    if unexpected:
        print(
            f'[bold red]ERROR:[/bold red] Found {len(unexpected)} unexpected keys in user config file ([cyan]{config_path}[/cyan]):'
        )
        for k in sorted(unexpected):
            print(
                f'\t[red]?[/red] {k}: {user_config[k]}'
            )
    print(
        f'Run [bold]evaluator config reset[/bold] to reset user configuration file with default values.\n'
    )
    raise typer.Exit(1)


# ====================
# Define subcommand: reset
# ====================
@evaluatorConfig.command(rich_help_panel="Config Commands")
def reset(force: Annotated[
        bool,
        typer.Option('--force', help='Skip confirmation prompt and immediately overwrite config.toml file.'),
    ] = False) -> None:
    '''
    Overwrites the users config file with EValuator's built-in default values.
    Includes a confirmation prompt unless --force supplied.
    '''
    # Get path to config.toml file for user OS
    config_path = userConfigPath()
    # if --force flag wasn't provided:
    if not force:
        print(f'\n[bold yellow]WARNING:[/bold yellow] This will overwrite [cyan]{config_path}[/cyan] with the EValuator default values.')
        confirm = typer.confirm(f'All custom settings will be lost. Continue?')
        if not confirm:
            print("[dim]Reset cancelled.[/dim]\n")
            raise typer.Exit(0)
    try:
        defaults = loadDefaultConfig()
        writeUserConfig(defaults)
    except Exception as e:
        print(f"\n[bold red]Error:[/bold red] Failed to reset user config file at [cyan]{config_path}[/cyan]: {e}")
        raise typer.Exit(1)
    print(f'\n[bold green]SUCCESS:[/bold green] User config file [cyan]{config_path}[/cyan] reset to defaults.\n')


# ====================
# Define function: loadUserConfig
# ====================
def loadUserConfig() -> dict:
    '''
    TODO
    '''
    config_path = userConfigPath()
    if not config_path.exists():
        raise FileNotFoundError(f"No user config file found at {config_path}.")
    with config_path.open('rb') as f:
        return tomllib.load(f)

    
# ====================
# Define function: writeUserConfig
# ====================
def writeUserConfig(config: dict) -> None:
    '''
    Write the provided dictionary to a toml file at the supplied file path.
    '''
    config_path = userConfigPath()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open('wb') as f:
        tomli_w.dump(config, f)

# ====================
# Define function: flattenToml
# ====================
def flattenToml(d: dict, prefix: str="") -> dict:
    '''
    TODO
    '''
    out = {}
    for k,v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flattenToml(v, full_key))
        else:
            out[full_key] = v
    return out

# ====================
# Define function: internalConfigCheck
# ====================
def internalConfigCheck(config_path: Path, exists: bool = True) -> bool:
    # Should the function check if the file exists?
    if exists:
        # Does the file exist?
        if config_path.exists():
            # If yes and yes, return nothing: all good!
            return True
        else:
            # If yes and no, return warning that file doesn't exist
            print(
                f'\n[bold yellow]Warning:[/bold yellow] No user config file exists at [cyan]{config_path}[/cyan]\nRun [bold]evaluator config init[/bold] to create a configuration file with default settings.\n'
            )
            return False
    # Or should it check that the file DOESN'T exist?
    else:
        # Does the file exist?
        if config_path.exists():
            # If checking doesn't exist and it does, return warning that file exists
            print(
                f'\n[bold yellow]Warning:[/bold yellow] User config file already exists at [cyan]{config_path}[/cyan]\nRun [bold]evaluator config reset[/bold] to reset configuration to default settings.\n'
            )
            return False
        else:
            # If checking doesn't exist and it doesn't, return nothing: all good!
            return True
        
def printConfigTable(user_config: dict, default_config: dict) -> None:
    '''
    Print a rich table comparing user config values against bundled defaults.
    Rows where the user value differs from the default are highlighted.
    '''
    # Set up rich console
    console = Console()
    # Define layout of rich table
    table = Table(
        title="EValuator configuration",
        show_header=True,
        header_style="bold",
        show_lines=False,
    )
    # Add columns to rich table
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Current value", justify="right")
    table.add_column("Default value", justify="right", style="dim")
    table.add_column("", width=2)    # status column
    # Loop through each key in default config
    for key in sorted(default_config.keys()):
        # Extract default and user values
        default_val = default_config[key]
        user_val = user_config.get(key, "[bold red]MISSING[/bold red]")
        # Work out if user option is different to default
        changed = str(user_val) != str(default_val)
        status = "[yellow]≠[/yellow]" if changed else "[green]✓[/green]"
        user_str = f"[yellow]{user_val}[/yellow]" if changed else str(user_val)
        # Add row to table
        table.add_row(key, user_str, str(default_val), status)
    # Print table
    console.print(table)