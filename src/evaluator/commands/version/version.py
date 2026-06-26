'''
=======================================
EValuator: PRINT VERSION
=======================================
'''
# ====================
# Import external dependencies
# ====================
import typer
from importlib.metadata import version
from rich import print

# ====================
# Define command: version
# ====================
def printVersion():
    print(f"\nRunning EValuator version: v{version('evaluator')}\n")
    typer.Exit(0)