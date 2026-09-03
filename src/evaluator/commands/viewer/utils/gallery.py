'''
=======================================
EValuator: VIEWER GALLERY SCANNING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import csv, os
import numpy as np
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import io as ioutil
from evaluator.commands.viewer.utils.stems import tomo_stem

# ====================
# Pipeline stages
# ====================
STAGES = ('raw', 'segmentations', 'labelled', 'model', 'analyse')

# ====================
# Define dataclasses
# ====================
@dataclass
class ResultSet:
    '''
    One tomogram's processed output, resolved across stage directories
    '''
    stem: str
    labelled_mrc: Path | None
    fitted_mrc: Path | None
    raw_mrc: Path | None
    binary_mrc: Path | None
    analyse_csv: Path | None
    model_results_path: Path | None
    n_vesicles: int
    n_reliable: int | None
    evaluator_dir: Path | None = None

# ====================
# Define helper functions
# ====================
def _first_existing(*paths: Path | None) -> Path | None:
    '''
    Returns the first path in the list that exists, or None
    '''
    return next((p for p in paths if p is not None and p.exists()), None)

def _count_labels(labelled_mrc: Path) -> int:
    '''
    Returns the number of distinct non-zero label ids in a labelled MRC.

    Reads the mmap slab by slab and unions per-slice uniques so the whole
    volume is never materialised in memory at once (the old np.asarray(f.data)
    copy was the scan bottleneck for large tomograms).
    '''
    import mrcfile

    seen: set[int] = set()
    with mrcfile.mmap(str(labelled_mrc), mode='r', permissive=True) as f:
        data = f.data
        if data is None:
            return 0
        if data.ndim < 3:
            seen.update(int(v) for v in np.unique(data))
        else:
            for z in range(data.shape[0]):
                seen.update(int(v) for v in np.unique(data[z]))
    seen.discard(0)
    return len(seen)

def _count_labels_worker(item: tuple[str, str]) -> tuple[str, int]:
    '''
    Pool worker: (stem, path) -> (stem, label count). Never raises.
    '''
    stem, path = item
    try:
        return stem, _count_labels(Path(path))
    except Exception:
        return stem, 0

def _counts_from_analyse_csv(path: Path) -> dict[str, int]:
    '''
    Returns {stem: row count} from a combined analyse results CSV, keyed by the
    'tomogram' column (a segmentation filename) with known suffixes stripped.
    Empty dict if the file is unreadable or has no 'tomogram' column.
    '''
    counts: Counter[str] = Counter()
    try:
        with path.open(newline='') as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames or 'tomogram' not in reader.fieldnames:
                return {}
            for row in reader:
                name = (row.get('tomogram') or '').strip()
                if not name:
                    continue
                counts[tomo_stem(name)] += 1
    except OSError:
        return {}
    return dict(counts)

def _names_in_dir(directory: Path | None, pattern: str = '*.mrc') -> frozenset[str]:
    '''
    Returns the set of filenames matching pattern in a directory, or an empty set if the directory is missing
    '''
    if directory is None or not directory.is_dir():
        return frozenset()
    return frozenset(p.name for p in directory.glob(pattern))

def _stem_map(names: frozenset[str]) -> dict[str, str]:
    '''
    Maps each file's canonical tomogram stem to its filename (last write wins)
    '''
    return {tomo_stem(name): name for name in names}

def _pick(directory: Path | None, names: frozenset[str], *candidates: str) -> Path | None:
    '''
    Returns directory / first candidate filename present in names, else None
    '''
    if directory is None:
        return None
    return next((directory / c for c in candidates if c in names), None)

# ====================
# Default stage directories
# ====================
def default_stage_dirs(root: Path) -> dict[str, Path | None]:
    '''
    Guess each stage directory from common subfolder names under root
    '''
    candidates = {
        'raw': ('raw', 'raw_tomograms', 'tomograms'),
        'segmentations': ('segmentations', 'segmented', 'segment', 'seg'),
        'labelled': ('labelled', 'evaluator/label', 'label'),
        'model': ('model', 'evaluator/model'),
        'analyse': ('analyse', 'evaluator/analyse', 'analysis'),
    }
    return {
        stage: next((root / name for name in names if (root / name).is_dir()), None)
        for stage, names in candidates.items()
    }


# ====================
# Define scan function
# ====================
ProgressFn = Callable[..., None]

def scan_stage_dirs(
    stage_dirs: dict[str, Path | None],
    progress: ProgressFn | None = None,
) -> list[ResultSet]:
    '''
    Scan stage directories and return one ResultSet per stem.

    progress(key, message, current=None, total=None) is called at each step so
    the caller can surface a verbose status; label counting for volumes with no
    cheaper vesicle count is done in parallel.
    '''
    _emit: ProgressFn = progress or (lambda *a, **k: None)

    raw_d = stage_dirs.get('raw')
    seg_d = stage_dirs.get('segmentations')
    lab_d = stage_dirs.get('labelled')
    mod_d = stage_dirs.get('model')
    ana_d = stage_dirs.get('analyse')

    # Model results files: per-file '<stem>_model_results.{csv,json}' (as written by
    # the model command) plus the legacy shared 'model_results.{csv,json}'. Records
    # are keyed per stem by their source_file, and the file each stem came from is
    # kept so the tomogram page can load just that stem's results.
    _emit('model', 'Reading model results files...')
    records_by_stem: dict[str, list[dict]] = {}
    results_path_by_stem: dict[str, Path] = {}
    if mod_d and mod_d.is_dir():
        results_files = sorted(
            {p for pat in ('*_model_results.csv', '*_model_results.json',
                           'model_results.csv', 'model_results.json')
             for p in mod_d.glob(pat)}
        )
        for results_path in results_files:
            for record in ioutil.read_results(results_path)[0]:
                source_file = record.get('source_file')
                if source_file:
                    stem = tomo_stem(source_file)
                    records_by_stem.setdefault(stem, []).append(record)
                    results_path_by_stem.setdefault(stem, results_path)
    _emit('model', f'Model results: {len(records_by_stem)} stems with records')

    # Per-stem vesicle counts from a combined analyse CSV (cheap: one file read)
    shared_analyse = _first_existing(
        *([ana_d / 'evaluator-analyse_results.csv'] if ana_d else []),
    )
    analyse_counts: dict[str, int] = {}
    if shared_analyse:
        _emit('analyse', 'Reading analyse results CSV...')
        analyse_counts = _counts_from_analyse_csv(shared_analyse)
        _emit('analyse', f'Analyse results: {len(analyse_counts)} stems with rows')

    # List each directory once; resolve per-stem paths by membership
    _emit('list', 'Listing stage directories...')
    raw_names = _names_in_dir(raw_d)
    seg_names = _names_in_dir(seg_d)
    lab_names = _names_in_dir(lab_d)
    mod_names = _names_in_dir(mod_d)
    ana_names = _names_in_dir(ana_d, '*.csv')

    # Canonical stem -> actual filename for each stage that names files per tomogram
    raw_map = _stem_map(raw_names)
    seg_map = _stem_map(seg_names)
    lab_map = _stem_map(lab_names)

    stems = sorted(
        set(raw_map)
        | set(seg_map)
        | set(lab_map)
        | {tomo_stem(name) for name in mod_names}
        | set(records_by_stem),
    )
    _emit('resolve', f'Resolving paths for {len(stems)} stems...', 0, len(stems))

    # First pass: resolve paths and any count we can get without reading a volume
    partials: list[dict] = []
    need_count: list[tuple[str, str]] = []  # (stem, labelled_mrc path) for parallel counting
    for i, stem in enumerate(stems):
        raw_mrc = (raw_d / raw_map[stem]) if stem in raw_map else None
        binary_mrc = (seg_d / seg_map[stem]) if stem in seg_map else None
        labelled_mrc = (lab_d / lab_map[stem]) if stem in lab_map else None
        fitted_mrc = _pick(
            mod_d, mod_names,
            f'{stem}_labelled_model_fitted.mrc', f'{stem}_model_fitted.mrc',
            f'{stem}_fitted.mrc', 'model_fitted.mrc',
        )
        analyse_csv = shared_analyse or _pick(ana_d, ana_names, f'{stem}_analyse.csv', f'{stem}.csv')

        stem_records = records_by_stem.get(stem, [])
        has_model_output = bool(stem_records) and fitted_mrc is not None
        n_reliable = (
            sum(1 for r in stem_records if r.get('reliability', {}).get('is_reliable'))
            if stem_records else None
        )

        n_vesicles: int | None
        if stem_records:
            n_vesicles = len(stem_records)
        elif stem in analyse_counts:
            n_vesicles = analyse_counts[stem]
        elif labelled_mrc is not None and labelled_mrc.exists():
            n_vesicles = None  # filled in by the parallel label count below
            need_count.append((stem, str(labelled_mrc)))
        else:
            n_vesicles = 0

        partials.append({
            'stem': stem,
            'labelled_mrc': labelled_mrc,
            'fitted_mrc': fitted_mrc if has_model_output else None,
            'raw_mrc': raw_mrc,
            'binary_mrc': binary_mrc,
            'analyse_csv': analyse_csv,
            'model_results_path': results_path_by_stem.get(stem) if has_model_output else None,
            'n_vesicles': n_vesicles,
            'n_reliable': n_reliable,
        })
        if (i + 1) % 200 == 0 or i + 1 == len(stems):
            _emit('resolve', f'Resolved {i + 1}/{len(stems)} stems...', i + 1, len(stems))

    # Second pass: count labels for the remaining volumes in parallel
    counts: dict[str, int] = {}
    total = len(need_count)
    if total:
        workers = min(total, max(1, (os.cpu_count() or 2)))
        _emit('count', f'Counting labels in {total} volume(s) using {workers} worker(s)...', 0, total)
        done = 0
        try:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for stem, count in pool.map(_count_labels_worker, need_count, chunksize=4):
                    counts[stem] = count
                    done += 1
                    if done % 25 == 0 or done == total:
                        _emit('count', f'Counted labels in {done}/{total} volume(s)...', done, total)
        except Exception as exc:  # pool unavailable -> fall back to sequential
            _emit('count', f'Parallel count unavailable ({exc}); counting sequentially...', done, total)
            for stem, path in need_count:
                if stem in counts:
                    continue
                counts[stem] = _count_labels_worker((stem, path))[1]
                done += 1
                if done % 25 == 0 or done == total:
                    _emit('count', f'Counted labels in {done}/{total} volume(s)...', done, total)

    result_sets = [
        ResultSet(
            stem=p['stem'],
            labelled_mrc=p['labelled_mrc'],
            fitted_mrc=p['fitted_mrc'],
            raw_mrc=p['raw_mrc'],
            binary_mrc=p['binary_mrc'],
            analyse_csv=p['analyse_csv'],
            model_results_path=p['model_results_path'],
            n_vesicles=p['n_vesicles'] if p['n_vesicles'] is not None else counts.get(p['stem'], 0),
            n_reliable=p['n_reliable'],
        )
        for p in partials
    ]
    _emit('done', f'{len(result_sets)} results resolved')
    return result_sets

# ====================
# Mid-slice 2D preview (thumbnail gallery)
# ====================
def midslice_preview(path: Path, is_label: bool = False) -> np.ndarray:
    '''
    Return the central Z slice of an MRC as a uint8 greyscale image, using mmap so only one slice read instead of volume
    is_label: normalise by max (label ids) instead of a 1-99 percentile stretch
    '''
    import mrcfile

    with mrcfile.mmap(str(path), mode='r', permissive=True) as f:
        z = f.data.shape[0] // 2
        sl = np.asarray(f.data[z], dtype=np.float32)

    if is_label:
        top = sl.max()
        img = sl / top if top > 0 else sl
    else:
        lo, hi = np.percentile(sl, [1, 99])
        img = np.clip((sl - lo) / (hi - lo + 1e-9), 0, 1)
    return (img * 255).astype(np.uint8)
