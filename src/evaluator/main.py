'''
EValuator entry point shim.
Re-exports the root typer app from cli.main so that the pyproject.toml
script target (evaluator.main:evaluator) continues to work without change.
'''
from evaluator.cli.cli import evaluator

__all__ = ["evaluator"]