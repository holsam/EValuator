'''
=======================================
EValuator: SEGMENTATION EV LABELLING
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
from evaluator.commands.label import label as labelFuncs

# ====================
# Initialise typer as evaluatorLabel
# ====================
evaluatorLabel = typer.Typer(
    add_completion=False,
)

# ====================
# Define command: label
# ====================
@evaluatorLabel.command(help='Label connected components in a segmentation MRC',rich_help_panel='Component Identification')
def label(
    # Define segmentation argument: path to a binary segmentation MRC file
    segmentation: Annotated[
        Path,
        typer.Argument(
            help='Path to either a single binary segmentation MRC (e.g. MemBrain-seg output) or a directory of segmentation MRC files',
            exists=True,
            file_okay=True,
            dir_okay=True,
            readable=True,
        )
    ],
    # Define output option: output directory, defaults to current working directory
    output: Annotated[
        Optional[Path],
        typer.Option(
            '-o', '--out-dir',
            help='Path to output directory, outputs will be written under ".../evaluator/label/"',
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path('.'),
    min_arc_coverage: Annotated[
        Optional[float],
        typer.Option('--min-arc-coverage', help='Override configuration minimum arc coverage parameter for this run', min=0, max=1)
    ] = None,
    minimum_diameter_nm: Annotated[
        Optional[float],
        typer.Option('--min-diameter', help='Override configuration minimum diameter parameter for this run')
    ] = None,
    maximum_diameter_nm: Annotated[
        Optional[float],
        typer.Option('--max-diameter', help='Override configuration maximum diameter parameter for this run')
    ] = None,
    jobs: Annotated[
        Optional[int],
        typer.Option('-j', '--jobs', help='Maximum parallel worker processes (default: CPU count)', min=1, rich_help_panel='Batch Options')
    ] = None,
):
    '''
    Label connected components in a binary segmentation MRC and write a labelled MRC
    '''
    if minimum_diameter_nm is not None and maximum_diameter_nm is not None and minimum_diameter_nm >= maximum_diameter_nm:
        raise typer.BadParameter(f'Diameters are not compatible.')

    labelFuncs.label_batch(
        segmentation,
        output,
        max_workers=jobs,
        min_arc_coverage=min_arc_coverage,
        minimum_diameter_nm=minimum_diameter_nm,
        maximum_diameter_nm=maximum_diameter_nm,
    )