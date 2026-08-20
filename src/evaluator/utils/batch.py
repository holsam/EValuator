'''
=======================================
EValuator: BATCH PROCESSING UTILITIES
=======================================
Functions for resolving file/directory CLI inputs into a list of MRC files, and running per-file work across a process pool.
'''

# ====================
# Import external dependencies
# ====================
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from typing import Callable, TypeVar

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils.settings import lg
from evaluator.utils import mrc as mrcutil

T = TypeVar('T')

# =========================
# DEFINE FUNCTION: resolve_mrc_inputs
# =========================
def resolve_mrc_inputs(input_path: Path, pattern: str = '*.mrc') -> list[Path]:
    '''
    Resolve a CLI input path (file or directory) into a sorted list of valid MRC files, logging invalid files
    '''
    if input_path.is_file():
        candidates = [input_path]
    else:
        candidates = sorted(input_path.glob(pattern))
    valid = [f for f in candidates if mrcutil.validateMRCFile(f)]
    for f in candidates:
        if f not in valid:
            lg.warning(f'{f} is not a valid MRC file and will not be processed.')
    if not valid:
        lg.error(f'No valid MRC files found in input: {input_path}.')
    return valid

# =========================
# DEFINE FUNCTION: run_batch
# =========================
def run_batch(
    files: list[Path],
    worker: Callable[[Path], T],
    max_workers: int | None = None,
    desc: str = 'Files processed',
) -> list[T]:
    '''
    Run worker over files in parallel, skipping (and logging) files if worker raises (returns successful results in file order)
    '''
    if max_workers if not None and max_workers <= 0:
        max_workers = None
    results: dict[Path, T] = {}
    with ProcessPoolExecutor(max_workers=max_workers) as pool, logging_redirect_tqdm():
        futures = {pool.submit(worker, f): f for f in files}
        for future in tqdm(as_completed(futures), total=len(files), desc=desc):
            f = futures[future]
            try:
                results[f] = future.result()
            except Exception as e:
                lg.warning(f'Failed to process {f.name}: {e}')
    return [results[f] for f in files if f in results]