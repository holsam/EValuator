'''
=======================================
EValuator: CONFIGURATION MANAGEMENT
=======================================
'''
# ====================
# Import external dependencies
# ====================
import tomllib, tomli_w, typer
from pathlib import Path
from rich import print
from rich.console import Console
from rich.table import Table
from typing import Annotated

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import loadDefaultConfig, userConfigPath

# ====================
# Define subcommand: init
# ====================
def config_init():
    '''
    Create a user config file populated with default settings in the OS config directory.
    '''
    print()
    config_path = userConfigPath()
    if not internalConfigCheck(config_path, exists=False):
        return
    try:
        defaults = loadDefaultConfig()
        writeUserConfig(defaults)
        print(f'[bold green]SUCCESS:[/bold green] User config file written to [cyan]{config_path}[/cyan]\n')
    except Exception as e:
        print(f'[bold red]ERROR:[/bold red] Failed to write user config file to [cyan]{config_path}[/cyan]: {e}.\n')
        raise typer.Exit(1)

# ====================
# Define subcommand: exists
# ====================
def config_exists() -> None:
    '''
    Report whether a user config file exists and the expected file path.
    '''
    print()
    config_path = userConfigPath()
    if config_path.exists():
        print(f"[bold green]SUCCESS:[/bold green] User config file found at [cyan]{config_path}[/cyan]\n")
    else:
        print(f'[bold yellow]WARNING:[/bold yellow] No user config file found at [cyan]{config_path}[/cyan]\nRun [bold]evaluator config init[/bold] to create one.\n')
        raise typer.Exit(1)

# ====================
# Define subcommand: list
# ====================
def config_list() -> None:
    '''
    Print the current config values, highlighting any user values which differ from EValuator defaults.
    '''
    config_path = userConfigPath()
    try:
        default_config = flattenToml(loadDefaultConfig())
    except tomllib.TOMLDecodeError as e:
        print(f'[bold red]ERROR:[/bold red] Could not parse default config file: {e}.\n')
        raise typer.Exit(1)
    if internalConfigCheck(config_path, exists=True):
        print(f'[bold blue]Current config settings:[/bold blue] user config file ([cyan]{config_path}[/cyan]).\n')
        try:
            user_config = loadUserConfig()
        except tomllib.TOMLDecodeError as e:
            print(f'[bold red]ERROR:[/bold red] Could not parse user config file: {e}.\n')
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
def config_verify() -> None:
    '''
    Verify that all expected keys are present in the current user config file.
    Exits with non-zero code if missing or unexpected keys are found.
    '''
    config_path = userConfigPath()
    if not internalConfigCheck(config_path, exists=True):
        raise typer.Exit(1)
    try:
        user_config = flattenToml(loadUserConfig())
        default_config = flattenToml(loadDefaultConfig())
    except tomllib.TOMLDecodeError as e:
        print(f'[bold red]ERROR:[/bold red] Could not parse config file: {e}.\n')
        raise typer.Exit(1)
    missing = [k for k in default_config if k not in user_config]
    unexpected = [k for k in user_config if k not in default_config]
    if not missing and not unexpected:
        print(f'[bold green]SUCCESS:[/bold green] User config file ([cyan]{config_path}[/cyan]) is valid.\n')
        return
    if missing:
        print(f'[bold red]ERROR:[/bold red] Found {len(missing)} missing keys in user config file ([cyan]{config_path}[/cyan]):')
        for k in sorted(missing):
            print(f'\t[red]✗[/red] {k} [dim](expected: {default_config[k]})[/dim]')
    if unexpected:
        print(f'[bold red]ERROR:[/bold red] Found {len(unexpected)} unexpected keys in user config file ([cyan]{config_path}[/cyan]):')
        for k in sorted(unexpected):
            print(f'\t[red]?[/red] {k}: {user_config[k]}')
    print(f'Run [bold]evaluator config reset[/bold] to reset user configuration file with default values.\n')
    raise typer.Exit(1)

# ====================
# Define subcommand: reset
# ====================
def config_reset(
    force: Annotated[
        bool,
        typer.Option('--force', help='Skip confirmation prompt and immediately overwrite config.toml.'),
    ] = False
) -> None:
    '''
    Overwrite the user config file with EValuator's built-in default values.
    Includes a confirmation prompt unless [bold]--force[/bold] is supplied.
    '''
    config_path = userConfigPath()
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
    Load and return the user config file as a dictionary.
    Raises FileNotFoundError if no user config file exists.
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
    Write the provided dictionary to the user config file path as TOML.
    '''
    config_path = userConfigPath()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open('wb') as f:
        tomli_w.dump(config, f)

# ====================
# Define function: flattenToml
# ====================
def flattenToml(d: dict, prefix: str = "") -> dict:
    '''
    Recursively flatten a nested TOML dictionary to dot-separated keys.
    '''
    out = {}
    for k, v in d.items():
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
    '''
    Check whether the user config file exists (or does not exist), printing
    appropriate messages. Returns True if the check passes.
    '''
    if exists:
        if config_path.exists():
            return True
        else:
            print(f'\n[bold yellow]Warning:[/bold yellow] No user config file exists at [cyan]{config_path}[/cyan]\nRun [bold]evaluator config init[/bold] to create a configuration file with default settings.\n')
            return False
    else:
        if config_path.exists():
            print(f'\n[bold yellow]Warning:[/bold yellow] User config file already exists at [cyan]{config_path}[/cyan]\nRun [bold]evaluator config reset[/bold] to reset configuration to default settings.\n')
            return False
        else:
            return True

# ====================
# Define function: printConfigTable
# ====================
def printConfigTable(user_config: dict, default_config: dict) -> None:
    '''
    Print a rich table comparing user config values against bundled defaults.
    Rows where the user value differs from the default are highlighted.
    '''
    console = Console()
    table = Table(
        title="EValuator configuration",
        show_header=True,
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Current value", justify="right")
    table.add_column("Default value", justify="right", style="dim")
    table.add_column("", width=2)
    for key in sorted(default_config.keys()):
        default_val = default_config[key]
        user_val = user_config.get(key, "[bold red]MISSING[/bold red]")
        changed = str(user_val) != str(default_val)
        status = "[yellow]≠[/yellow]" if changed else "[green]✓[/green]"
        user_str = f"[yellow]{user_val}[/yellow]" if changed else str(user_val)
        table.add_row(key, user_str, str(default_val), status)
    console.print(table)