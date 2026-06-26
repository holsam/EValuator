'''
=======================================
EValuator: PRINT VERSION
=======================================
'''
# ====================
# Import external dependencies
# ====================
from importlib.metadata import PackageNotFoundError, version
from rich import print

# ====================
# Define command: version
# ====================
def printVersion():
    try:
        v = version('evaluator')
    except PackageNotFoundError:
        v = '? (package not installed)'
    print(f'\nRunning EValuator version: [bold cyan]v{v}[/bold cyan]\n')
    raise SystemExit(0)