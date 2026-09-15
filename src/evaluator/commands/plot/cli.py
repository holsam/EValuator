'''
=======================================
EValuator: ANALYSE/MODEL RESULTS PLOTTING
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer
from pathlib import Path
from typing import Annotated, Optional

# ====================
# Import EValuator utilities
# ====================
from evaluator.commands.plot import plot as plotFuncs

# ====================
# Initialise typer as evaluatorPlot
# ====================
evaluatorPlot = typer.Typer(
    add_completion=False,
)

VALID_SECTIONS = ["distributions", "qc", "scatter", "concordance", "compare"]

@evaluatorPlot.command(help='Generate plots from evaluator analyse and/or model output', rich_help_panel='Component Analysis')
def plot(
    analyse_input: Annotated[
        Optional[Path],
        typer.Option('--analyse', help='Path to an analyse results CSV, or a sample sheet referencing multiple', exists=True, file_okay=True, dir_okay=False, readable=True)
    ] = None,
    model_input: Annotated[
        Optional[Path],
        typer.Option('--model', help='Path to a model results file (JSON or CSV), or a sample sheet referencing multiple', exists=True, file_okay=True, dir_okay=False, readable=True)
    ] = None,
    output: Annotated[
        Path,
        typer.Option('-o', '--out-dir', help='Path to output directory, outputs written under ".../evaluator/plot/"', file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    section: Annotated[
        Optional[list[str]],
        typer.Option('--section', help=f"Section(s) to run: {', '.join(VALID_SECTIONS)} (repeatable)")
    ] = None,
    all_sections: Annotated[
        bool,
        typer.Option('--all', help='Run every applicable section')
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option('--overwrite', help='Overwrite existing section outputs instead of skipping them')
    ] = False,
    rscript: Annotated[
        Optional[Path],
        typer.Option('--rscript', help='Path to the Rscript binary (default: resolved from PATH)')
    ] = None,
):
    '''
    Generate plots and summary tables from `analyse` and/or `model` output.
    '''
    if analyse_input is None and model_input is None:
        raise typer.BadParameter('At least one of --analyse or --model must be provided.')
    plotFuncs.run_plot(
        analyse_input,
        model_input,
        output,
        sections=section,
        all_sections=all_sections,
        overwrite=overwrite,
        rscript=rscript,
    )
