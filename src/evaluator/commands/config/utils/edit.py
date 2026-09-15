'''
=======================================
EValuator: CONFIGURATION FILE EDITING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import click, tomlkit
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import config

# ====================
# Define helper functions
# ====================
def _warn_if_invalid(config_path: Path) -> None:
    '''Raise exception if configuration file isn't't valid'''
    try:
        config.read_config(config_path)
    except Exception as e:
        click.echo(f'Warning: {e}', err=True)

def _prompt_type(value: object) -> type:
    '''Return expected type of answer for a prompt'''
    if isinstance(value, bool):
        return bool
    if isinstance(value, int):
        return int
    if isinstance(value, float):
        return float
    return str

def _edit_stepwise(config_path: Path) -> None:
    '''Walk through each configuration setting and prompt for modifications'''
    doc = tomlkit.parse(config_path.read_text(encoding='utf-8'))
    def walk(table, prefix: str = '') -> None:
        for key, value in list(table.items()):
            dotted = f'{prefix}{key}'
            if isinstance(value, dict):
                walk(value, prefix=f'{dotted}.')
            elif isinstance(value, list):
                click.echo(f'  (skipping {dotted}: edit array values in the file directly)')
            else:
                table[key] = click.prompt(dotted, default=value, type=_prompt_type(value))
    walk(doc)
    # Validate the candidate before writing anything back
    new_text = tomlkit.dumps(doc)
    candidate_path = config_path.with_suffix('.toml.candidate')
    candidate_path.write_text(new_text, encoding='utf-8')
    try:
        config.read_config(candidate_path)
    except Exception as e:
        candidate_path.unlink(missing_ok=True)
        raise click.ClickException(f'Edited config is invalid, nothing written: {e}')
    candidate_path.unlink(missing_ok=True)
    config_path.write_text(new_text, encoding='utf-8')

# ====================
# Define configuration edit function
# ====================
def edit_config(config_path: Path, *, stepwise: bool) -> None:
    '''Edit a config file in place, then validate it'''
    if stepwise:
        _edit_stepwise(config_path)
        # interactive validation happens before write; nothing more to do
        return
    click.edit(filename=str(config_path))  # opens $EDITOR on the file
    _warn_if_invalid(config_path)