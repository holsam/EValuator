'''
=======================================
EValuator: APPLICATION SETTINGS & STARTUP
=======================================
Provides the shared logger instance, config loading utilities,
and the startup splash function.
Loaded at import time so that `config` and `lg` can be imported
directly by command modules.
'''

# ====================
# Import external dependencies
# ====================
import logging, tomllib
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir
from rich import print

# =========================
# INITIALISE LOGGER
# =========================
lg = logging.getLogger("__name__")

# ====================
# Define function: userConfigPath
# ====================
def userConfigPath() -> Path:
    '''
    Returns the file path <OS config directory>/evaluator/config.toml depending on the OS of running environment:
        Linux/macOS : ~/.config/evaluator/config.toml
        Windows     : %APPDATA%\\evaluator\\config.toml
    '''
    return Path(user_config_dir("evaluator"), "config.toml")

# ====================
# Define function: loadDefaultConfig
# ====================
def loadDefaultConfig() -> dict:
    '''
    Load the bundled default config.toml from the installed package.
    '''
    with pkg_files('evaluator').joinpath('config.toml').open('rb') as defaultconfig:
        return tomllib.load(defaultconfig)

# ====================
# Load config at module import time
# ====================
user_config_path = userConfigPath()
if user_config_path.exists():
    with user_config_path.open('rb') as _userconfig:
        config = tomllib.load(_userconfig)
else:
    config = loadDefaultConfig()

# ====================
# Define function: initEvaluator
# ====================
def initEvaluator():
    '''
    Print the EValuator startup splash to the terminal.
    '''
    print(f"\n[bold]EValuator[/bold] :microscope-text:")
    print(f"A command line tool for automated morphological analysis and visualisation of extracellular vesicles (EVs) from cryo-electron tomography (cryo-ET) data.")