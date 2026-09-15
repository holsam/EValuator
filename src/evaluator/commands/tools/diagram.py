'''
=======================================
EValuator: DIAGRAM VISUALISATION UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import typer
from pathlib import Path
from typing import Annotated

# ====================
# Import diagram script and defaults
# ====================
from evaluator.commands.tools.diagram_pipeline import diagram_pipeline, defaults

# ====================
# Initialise typer as evaluatorAnimate
# ====================
evaluatorDiagram = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Define command: diagram
# ====================
@evaluatorDiagram.command('pipeline')
def pipeline_diagram(
    output: Annotated[
        Path,
        typer.Option('-o', '--output', help='Output PNG path for the pipeline diagram'),
    ] = defaults.OUTPUT,
    downsample: Annotated[
        int,
        typer.Option('--downsample', help='Voxel downsample factor for rendering'),
    ] = defaults.DOWNSAMPLE,
):
    '''
    Render the EValuator pipeline, using real label/model output on test fixtures and synthetic partial-coverage (band/cap) examples
    '''
    diagram_pipeline.build_diagram(output, downsample=downsample)
