'''
=======================================
EValuator: VIEWER STREAMLIT DISPATCH
=======================================
'''

# ====================
# Import external dependencies
# ====================
import re, shutil, subprocess, webbrowser
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
# Define constants
# ====================

_URL = re.compile(r'\b(Local|Network|External)\s+URL\s*:', re.IGNORECASE)
# Lines from streamlit/tornado/uvicorn that are pure chrome or per-request noise -> demote to debug
_NOISE = re.compile(
    r'(Welcome to Streamlit|Gathering usage statistics|streamlit run'
    r'|Tornado|uvicorn|\d{3}\s+(GET|POST|HEAD)|HTTP/1\.[01]"|For better performance, install'
    r'|You can now view your Streamlit app)',
    re.IGNORECASE,
)

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

def resolve_port(port: int) -> int:
    '''
    Checks the given port isn't in use (if not 0) and returns
    '''
    if port != 0:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', port))
            s.shutdown(2)
            lg.warning(f'viewer | localhost:{port} is in use by another process, falling back to default')
            port = 0
        except socket.error:
            lg.debug(f'viewer | localhost:{port} is available for use')
        finally:
            s.close()
    return port

def dispatch(streamlit_bin: Path, root_dir: Path, port: int) -> None:
    '''
    Launch the Streamlit app as a foreground interactive process
    '''
    cmd = [
        str(streamlit_bin), 'run', str(_app_path()),
        '--server.port', str(port), 
        '--server.headless', 'true',
        '--browser.gatherUsageStats', 'false',
        '--global.showWarningOnDirectExecution', 'false',
        '--', str(root_dir),
    ]
    lg.info(f"viewer | launching: {' '.join(cmd)}")
    print('Starting EValuator viewer (Ctrl-C to stop)...', flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    opened=False
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if _URL.search(line):
                print(line.strip(), flush=True)
                m = re.search(r'https?://\S+', line)
                if m and not opened and 'local' in line.lower():
                    opened = True
                    webbrowser.open(m.group(0))
            else:
                (lg.debug if _NOISE.search(line) else lg.info)('viewer | %s', line)
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()