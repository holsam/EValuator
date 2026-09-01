'''
=======================================
EValuator: INTERACTIVE VESICLE VIEWER
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
from evaluator.commands.viewer import viewer as viewerFuncs

# ====================
# Initialise typer as evaluatorViewer
# ====================
evaluatorViewer = typer.Typer(
    add_completion=False,
)

# ====================
# Define command: viewer
# ====================
@evaluatorViewer.command(rich_help_panel='Component Visualisation')
def viewer(
    root: Annotated[
        Optional[Path],
        typer.Argument(help='Root directory to scan for evaluator output (label/model/analyse); can also be chosen from within the viewer', exists=True, file_okay=False, dir_okay=True)
    ] = None,
    port: Annotated[
        int,
        typer.Option('--port', help='Local port for the Streamlit server (default: resolved by OS)'),
    ] = 0,
    streamlit_bin: Annotated[
        Optional[Path],
        typer.Option('--streamlit-bin', help='Path to the streamlit binary (default: resolved from PATH)'),
    ] = None,
):
    '''
    Launch the interactive 3D vesicle viewer
    '''
    viewerFuncs.launch_viewer(root or Path.cwd(), port=port, streamlit_bin=streamlit_bin)
