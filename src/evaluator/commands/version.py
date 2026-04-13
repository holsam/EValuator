'''
=======================================
EValuator: PRINT VERSION
=======================================
'''
# ====================
# Import external dependencies
# ====================
import tomllib, typer
from importlib.resources import files as pkg_files
from rich import print

# ====================
# Define command: version
# ====================
def printVersion():
    with pkg_files('evaluator').joinpath('../../pyproject.toml').open('rb') as f:
        contents = tomllib.load(f)
    print(f"\nRunning EValuator version: v{contents['project']['version']}\n")
    typer.Exit(0)