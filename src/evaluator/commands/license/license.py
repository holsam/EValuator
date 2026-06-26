'''
=======================================
EValuator: PRINT LICENSE
=======================================
'''
# ====================
# Import external dependencies
# ====================
from importlib.resources import files as pkg_files
from pydoc import pager
from rich import print

# ====================
# Define command: license
# ====================
def printLicense():
    with pkg_files('evaluator').joinpath('../../LICENSE').open('r') as f:
        pager(f.read())
        print(f'\nEValuator is distributed under the [bold cyan]GPL-3.0 license[/bold cyan].\n')
    raise SystemExit(0)