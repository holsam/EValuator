'''
=======================================
EValuator: SEGMENTATION ANALYSIS PIPELINE
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
from evaluator.commands.analyse import analyse as analyseFuncs

# ====================
# Initialise typer as evaluatorAnalyse
# ====================
evaluatorAnalyse = typer.Typer(
    add_completion=False,
)

@evaluatorAnalyse.command(help='Run morphological analysis pipeline on labelled MRC files', rich_help_panel='Component Analysis')
def analyse(
    # Define input argument: path to a single labelled MRC or a directory of labelled MRC files
    input: Annotated[
        Path,
        typer.Argument(
            help="Path to either a single labelled MRC file (output of [bold]label[/bold]) or a directory of labelled MRC files",
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
            "-o", "--out-dir",
            help='Path to output directory, outputs will be written under ".../evaluator/analyse/"',
            file_okay=False,
            dir_okay=True,
            writable=True,
        )
    ] = Path("."),
    # Define optional configuration overrides
    fill_threshold: Annotated[
        Optional[float],
        typer.Option('--fill-threshold', help='Override configuration fill threshold parameter for this run', min=0, max=1)
    ] = None,
    qc_max_sphere_rmse_rel: Annotated[
        Optional[float],
        typer.Option('--qc-max-sphere-rmse-rel', help='Max best-fit-sphere relative RMSE for a vesicle-like component', min=0, rich_help_panel='Vesicle-Like Check Overrides')
    ] = None,
    qc_max_aspect_ratio: Annotated[
        Optional[float],
        typer.Option('--qc-max-aspect-ratio', help='Max major/minor axis ratio for a vesicle-like component', min=1, rich_help_panel='Vesicle-Like Check Overrides')
    ] = None,
    qc_min_solidity: Annotated[
        Optional[float],
        typer.Option('--qc-min-solidity', help='Min voxel-count / convex-hull-volume ratio for a vesicle-like component', min=0, max=1, rich_help_panel='Vesicle-Like Check Overrides')
    ] = None,
    qc_min_arc_coverage: Annotated[
        Optional[float],
        typer.Option('--qc-min-arc-coverage', help='Min fitted-sphere surface coverage for a non-enclosed component to still count as vesicle-like', min=0, max=1, rich_help_panel='Vesicle-Like Check Overrides')
    ] = None,
    qc_max_fit_points: Annotated[
        Optional[int],
        typer.Option('--qc-max-fit-points', help='Random-subsample size of component voxels used for the QC sphere fit / convex hull / arc grid', min=4, rich_help_panel='Vesicle-Like Check Overrides')
    ] = None,
    jobs: Annotated[
        Optional[int],
        typer.Option('-j', '--jobs', help='Maximum parallel worker processes (default: CPU count)', min=1, rich_help_panel='Batch Options')
    ] = None,
):
    '''
    Run post-processing pipeline on labelled EV segmentation files.
    '''
    analyseFuncs.analyse(
        input,
        output,
        fill_threshold=fill_threshold,
        qc_max_sphere_rmse_rel=qc_max_sphere_rmse_rel,
        qc_max_aspect_ratio=qc_max_aspect_ratio,
        qc_min_solidity=qc_min_solidity,
        qc_min_arc_coverage=qc_min_arc_coverage,
        qc_max_fit_points=qc_max_fit_points,
        max_workers=jobs,
    )
