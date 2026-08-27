'''
=======================================
EValuator: APPLICATION SETTINGS & STARTUP
=======================================
Provides the shared logger instance, config loading utilities, and the startup splash function. Loaded at import time so that `config` and `lg` can be imported directly by command modules.
'''

# ====================
# Import external dependencies
# ====================
import sys, time
from datetime import datetime
from loguru import logger as logger
from os import access, W_OK
from pathlib import Path
from rich import print

# ====================
# Define constants for logger setup
# ====================
DEFAULT_LOG_NAME = Path('evaluator.log')
LOG_FORMAT = '<dim>{time:YYYY-MM-DD HH:mm:ss}</> <lvl>[{level}]</> {message}'

# ====================
# Define class for logger, to proxy standard log methods with colours set to True
# ====================
class _EvaluatorLogger:
    def _log(self, level: str, message: str, *args, **kwargs) -> None:
        logger.opt(colors=True, depth=2).log(level, message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._log('DEBUG', message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._log('INFO', message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._log('WARNING', message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._log('ERROR', message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        self._log('CRITICAL', message, *args, **kwargs)

# ====================
# Define helper functions
# ====================
def _resolve_log_directory():
    '''
    Returns Path indicating which directory to write the log file within (follows hierarchy: current working directory -> home directory)
    '''
    dirs = [Path.cwd(), Path.home()]
    for d in dirs:
        d = d / 'evaluator'
        # If directory doesn't exist, try to create (logging warning if not possible)
        if not d.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.warning(f'Could not create log file parent directory {d}')
                continue
        # If directory is writable, return otherwise raise warning
        if access(d, W_OK):
            return d
        logger.warning(f'No write permissions for {d} to create log file')
    # If all options exhausted, raise an error
    raise PermissionError('No writable directory found for log file')

def _resolve_log_path(
    directory: Path,
) -> tuple[Path, bool]:
    '''
    Returns Path for log file avoiding collisions
    '''
    path = directory / DEFAULT_LOG_NAME
    if path.exists():
        file_counter = 1
        while True:
            path = directory / f'{DEFAULT_LOG_NAME.stem}-{file_counter}{DEFAULT_LOG_NAME.suffix}'
            if path.exists():
                file_counter += 1
            else:
                break
    return path

# ====================
# Define function: initEvaluator
# ====================
def configure_logging(level: str) -> Path:
    '''
    Returns Path to log file after configuring logging sinks
    '''
    # Remove default logging handler
    logger.remove()
    # Add terminal sink
    logger.add(sys.stderr, format=LOG_FORMAT, level=level, colorize=True)
    # Add a temporary buffer sink to catch any warning logs raised during log file directory resolution
    buffer: list[str] = []
    buffer_sink = logger.add(buffer.append, format=LOG_FORMAT, level=level, colorize=False)
    # Resolve log file directory/path and remove buffer sink
    log_dir = _resolve_log_directory()
    log_path = _resolve_log_path(log_dir)
    logger.remove(buffer_sink)
    # Based on mode, open log file as write or append
    with open(log_path, 'w', encoding='utf-8') as f:
        f.writelines(buffer)
    # Set up actual log file sink
    logger.add(log_path, format=LOG_FORMAT, level=level, colorize=False, mode='a')
    # Return log file path
    return log_path

# ====================
# Define function: initEvaluator
# ====================
def initEvaluator():
    '''
    Print the EValuator startup splash to the terminal.
    '''
    print(f"\n[bold]EValuator[/bold] :microscope-text:")
    print(f"A command line tool for automated morphological analysis and visualisation of extracellular vesicles (EVs) from cryo-electron tomography (cryo-ET) data.")

# =========================
# INITIALISE LOGGER
# =========================
lg = _EvaluatorLogger()
