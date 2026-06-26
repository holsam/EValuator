'''
=======================================
EValuator: PRINT LICENSE
=======================================
'''
# ====================
# Import external dependencies
# ====================
import typer
from importlib.resources import files as pkg_files
from rich import print

# ====================
# Define command: license
# ====================
def printLicense():
    with pkg_files('evaluator').joinpath('LICENSE').open('r') as f:
        print(f.read())
    typer.Exit(0)