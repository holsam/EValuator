'''
=======================================
EValuator: PLOT COMMAND R SCRIPT DISPATCH
=======================================
'''

# ====================
# Import external dependencies
# ====================
import shutil, subprocess
from importlib.resources import files as pkg_files
from pathlib import Path

# ====================
# Import internal EValuator dependencies
# ====================
from evaluator.utils.settings import lg

# ====================
# Define custom error classes
# ====================
class RscriptNotFoundError(RuntimeError):
    '''Raised when no usable Rscript binary can be resolved'''

class RscriptError(RuntimeError):
    '''Raised when an R script exits non-zero'''

# ====================
# Define Rscript dispatch functions
# ====================
def resolve_rscript(rscript: Path | None) -> Path:
    if rscript is not None:
        if not rscript.exists():
            raise RscriptNotFoundError(f'Rscript not found at {rscript}')
        return rscript
    found = shutil.which("Rscript")
    if found is None:
        raise RscriptNotFoundError('Rscript not found on PATH. Install R to PATH, or pass --rscript.')
    return Path(found)

def _script_path(name: str) -> Path:
    return Path(str(pkg_files('evaluator.commands.plot') / 'r' / name))

def dispatch(rscript_bin: Path, script_name: str, args: list[str]) -> None:
    '''
    Run r/<script_name> with positional args, streaming stderr as it's produced
    '''
    script = _script_path(script_name)
    cmd = [str(rscript_bin), str(script), *[str(a) for a in args]]
    lg.debug(f"plot | Running: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        lg.debug(f"plot | {script_name} stdout:\n{proc.stdout}")
    if proc.returncode != 0:
        raise RscriptError(f"{script_name} failed (exit {proc.returncode}):\n{proc.stderr}")
    if proc.stderr:
        lg.debug(f"plot | {script_name} stderr:\n{proc.stderr}")
