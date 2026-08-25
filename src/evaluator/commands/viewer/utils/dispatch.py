'''
=======================================
EValuator: VIEWER STREAMLIT DISPATCH
=======================================
'''

# ====================
# Import external dependencies
# ====================
import shutil, subprocess
from importlib.resources import files as pkg_files
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import lg

# ====================
# Define custom error classes
# ====================
class StreamlitNotFoundError(RuntimeError):
    '''Raised when no usable streamlit binary can be resolved'''

# ====================
# Define streamlit dispatch functions
# ====================
def resolve_streamlit(streamlit_bin: Path | None) -> Path:
    '''
    Returns a usable streamlit binary path from PATH or an override
    '''
    if streamlit_bin is not None:
        if not streamlit_bin.exists():
            raise StreamlitNotFoundError(f'streamlit not found at {streamlit_bin}')
        return streamlit_bin
    found = shutil.which('streamlit')
    if found is None:
        raise StreamlitNotFoundError('streamlit not found on PATH. Ensure evaluator was installed with its viewer dependencies, or pass --streamlit-bin.')
    return Path(found)

def _app_path() -> Path:
    '''
    Returns the packaged Streamlit entrypoint script path
    '''
    return Path(str(pkg_files('evaluator.commands.viewer') / 'app' / 'viewer.py'))

def dispatch(streamlit_bin: Path, root_dir: Path, port: int) -> None:
    '''
    Launch the Streamlit app as a foreground interactive process
    '''
    cmd = [str(streamlit_bin), 'run', str(_app_path()), '--server.port', str(port), '--', str(root_dir)]
    lg.info(f"viewer | launching: {' '.join(cmd)}")
    subprocess.run(cmd)
