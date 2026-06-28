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
from evaluator.utils import config

# ====================
# Import internal command utilities
# ====================
from evaluator.commands.config.utils import edit

# ====================
# Define config command logic function
# ====================
def run_config(path: Path, *, stepwise: bool) -> None:
    resolved = config.resolve_config(path)
    if resolved.existed:
        print(f'Editing configuration file: [cyan]{resolved.config_path}[/cyan]')
        edit.edit_config(resolved.config_path, stepwise=stepwise)
        return
    config.create_default_config(resolved.config_path)
    print(f'Created configuration file from defaults at: [cyan]{resolved.config_path}[/cyan]')
    if typer.confirm(text='Edit configuration file now', default=True, prompt_suffix='? '):
        edit.edit_config(resolved.config_path, stepwise=stepwise)
