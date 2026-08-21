'''
=======================================
EValuator: TOOLS CONSOLE UTILITY FUNCTIONS
=======================================
Functions for printing to terminal
'''

# ====================
# Import external dependencies
# ====================
import os, sys
from rich import print

# ====================
# DEFINE FUNCTIONS
# ====================
def print_divider():
    terminal_width = os.get_terminal_size().columns
    print(f'{"="*terminal_width}')

def print_header(command: str, subcommand: str):
    terminal_width = os.get_terminal_size().columns
    print(f'\n')
    print_divider()
    print(f'[bold]{command.upper()}: {subcommand.upper()}[/bold]')

def print_benchmark_parameters(params):
    print('Benchmark parameters:')
    for p in params:
        print(f'\t- {p}: {params.get(p)}')

def print_saved_file(message, path):
    print(f'{message}: [cyan]{path}[/cyan]')

def progress_bar(current_iter, total_iter):
    # Add one to account for Python indexing starting from 0
    actual_iter = total_iter + 1
    terminal_width = os.get_terminal_size().columns
    # Length of string: 'Progress N/N'
    text_width = len(f'Progress {actual_iter}/{actual_iter}')
    # If terminal is smaller than text_width, can't show anything so skip
    if terminal_width < text_width:
        return
    # Calculate width of progress bar as terminal width - text above (+ 1 for an extra space)
    progress_width = terminal_width - (text_width + 1)
    # If progress bar would be less than 10 characters, just show count increasing as progress bar becomes meaningless
    if progress_width < 10:
        sys.stdout.write(f'\rProgress {iteration}/{total+1}')
        sys.stdout.flush()
    else:
        fill_width = int(progress_width * current_iter // actual_iter)
        bar = '█' * fill_width + ' ' * (progress_width-fill_width)
        # Right-adjust current iteration to actual iteration (so changes from eg 9->10 don't make progress bar expand)
        current_iter = str(current_iter).rjust(len(str(actual_iter)))
        sys.stdout.write(f'\rProgress {bar} {current_iter}/{actual_iter}')
        sys.stdout.flush()
    if current_iter == total_iter:
        print()