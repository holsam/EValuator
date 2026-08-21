'''
=======================================
EValuator: R DEPENDENCY TOOLS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import json, shutil, subprocess, typer
from importlib.resources import files as pkg_files
from pathlib import Path
from rich import print
from typing import Annotated

# ====================
# Initialise typer as evaluatorRDeps
# ====================
evaluatorRDeps = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
)

# ====================
# Define helper functions
# ====================
def _check_rscript(rscript: str = 'Rscript'):
    if shutil.which(rscript) is None:
        print(f'[bold red]Error:[/] Rscript not callable at {rscript}')
        raise RuntimeError(f'Rscript not callable at {rscript}')

def _check_r_dependencies(rscript: str = 'Rscript') -> dict[str, list[str]] | None:
    _check_rscript(rscript)
    script_path = pkg_files('evaluator').joinpath(f'utils/r/deps/check_deps.R')
    result = subprocess.run([rscript, '--vanilla', str(script_path)], capture_output=True, text=True)
    # Parse returned result as JSON
    try:
        parsed = json.loads(result.stdout.strip())
        return parsed
    except json.JSONDecodeError as e:
        print(f'[bold red]Error:[/] could not parse dependency check output: {e}')
        raise SystemExit(1)

# ====================
# Define RscriptOption
# ====================
RscriptOption = Annotated[
    str,
    typer.Option('--rscript', help='Path to Rscript binary')
]

# ====================
# Define command: check
# ====================
@evaluatorRDeps.command('check')
def check_deps(rscript: RscriptOption = 'Rscript'):
    '''
    Check EValuator's required R dependencies are installed
    '''
    dependency_state = _check_r_dependencies(rscript)
    installed_deps = dependency_state['installed']
    missing_deps = dependency_state['missing']
    if len(installed_deps) > 0:
        print(f'[bold green]✓ Installed packages ({len(installed_deps)})[/bold green]: {", ".join(installed_deps)}')
    if len(missing_deps) > 0:
        print(f'[bold red]✗ Missing packages ({len(missing_deps)})[/bold red]: {", ".join(missing_deps)}')
        print('To install missing packages, run [bold]evaluator tools r-deps install[/bold]')
    print()

# ====================
# Define command: install
# ====================
@evaluatorRDeps.command('install')
def install_deps(rscript: RscriptOption = 'Rscript'):
    '''
    Install EValuator's required R dependencies
    '''
    dependency_state = _check_r_dependencies(rscript)
    missing_deps = dependency_state['missing']
    try:
        if len(missing_deps) > 0:
            print(f'{len(missing_deps)} {"dependencies need" if len(missing_deps) > 1 else "dependency needs"} to be installed: {", ".join(d for d in missing_deps)}')
            while True:
                user_confirmation = Confirm.ask('Install these packages? [dim](y/N)[/dim]', choices=['y','n'], default='n', case_sensitive=False, show_default=False, show_choices=False).lower()
                if user_confirmation in ['', 'n']:
                    print(f'No dependencies installed!')
                    break
                if user_confirmation == 'y':
                    script_path = pkg_files('evaluator').joinpath(f'utils/r/deps/install_deps.R')
                    process = subprocess.Popen([rscript, '--vanilla', str(script_path)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in process.stdout:
                        line = line.rstrip()
                        if line:
                            print(f'[dim]EVALUATOR R DEPENDENCY INSTALLATION:[/] {line}')
                    process.wait()
                    if process.returncode != 0:
                        print(f'[bold red]Error:[/] R dependency installation failed, see above output')
                        return
                    print(f'[bold green]Success:[/] R dependencies installed')
                    break
        else:
            print(f'[bold green]Success:[/] no dependencies missing!')
            return
    except Exception as e:
        print(f'[bold red]Error:[/] could not check missing dependencies: {e}')
    finally:
        print()