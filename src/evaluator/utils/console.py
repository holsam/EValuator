'''
Utility Functions: console management
'''
# -- Import external dependencies ----------------
import logging
from datetime import datetime
from rich import print
from rich.console import Console

# -- Define Msg class ----------------------------
class Msg():
    def __init__(self, command, message, level, timestamp = datetime.datetime.now()):
        self.command = command
        self.message = message
        self.timestamp = timestamp
        self.level = level
    
    def add(self):
        full_message = f'{self.timestamp}\t|\t{self.command}\t|\t{self.message}'
        if self.level == 'warn':
            lg.warning(full_message)
        if self.level == 'info':
            lg.info(full_message)
        if self.level == 'debug':
            lg.debug(full_message)

# -- Define initLogger function ------------------
def initLogger(
        debug: bool, 
        verbose: bool
    ):
    # Initialise logger
    global lg
    lg = logging.getLogger("EValuator")
    # Check if debug flag was provided, and if so set logging level to debug
    if debug:
        log_level = logging.DEBUG
    # Check if verbose flag was provided, and if so set logging level to information
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(datefmt='%Y-%m-%d %H:%M:%S', level = log_level)

# -- Define initConsole function -----------------
def initConsole():
    std_console = Console()
    err_console = Console()

# -- Define startMessage function ----------------
def startMessage():
    # Print top-level splash
    print(f"\n[bold]EValuator[/bold] :microscope-text:")
    print(f"A command line tool for automated morphological analysis and visualisation of extracellular vesicles (EVs) from cryo-electron tomography (cryo-ET) data.")

def printMessage():
    # 
    print(f'')

# lg.warning(f"{path.name}: voxel size not found in MRC header. Physical measurement units will be voxels.")