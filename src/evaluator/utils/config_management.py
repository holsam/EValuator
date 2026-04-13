'''
Utility Functions: config management
'''

# -- Import external dependencies ----------------
import tomllib
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir

# -- Define userConfigPath function --------------
def userConfigPath() -> Path:
    '''
    Returns the file path <OS config directory>/evaluator/config.toml depending on the OS of running environment:
        Linux/macOS : ~/.config/evaluator/config.toml
        Windows     : %APPDATA%\\evaluator\\config.toml
    '''
    return Path(user_config_dir("evaluator"), "config.toml")

# -- Define loadDefaultConfig function -----------
def loadDefaultConfig() -> dict:
    '''
    Load the bundled default config.toml from the installed package.
    '''    
    with pkg_files('evaluator').joinpath('config.toml').open('rb') as defaultconfig:
        return tomllib.load(defaultconfig)