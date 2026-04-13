'''
=======================================
EValuator: PRINT LICENSE
=======================================
'''
# ====================
# Import external dependencies
# ====================
import typer
from rich import print

# ====================
# Define command: license
# ====================
def printLicense():
    with open('./LICENSE', 'r') as licensefile:
        print(f"\n{licensefile.read()}")
    typer.Exit(0)