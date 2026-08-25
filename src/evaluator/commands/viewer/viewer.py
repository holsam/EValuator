'''
=======================================
EValuator: VIEWER LAUNCH ORCHESTRATION
=======================================
'''

# ====================
# Import external dependencies
# ====================
from pathlib import Path

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils import dispatch

# ====================
# Define launch function
# ====================
def launch_viewer(root: Path, port: int, streamlit_bin: Path | None) -> None:
    streamlit_bin = dispatch.resolve_streamlit(streamlit_bin)
    dispatch.dispatch(streamlit_bin, root_dir=root, port=port)
