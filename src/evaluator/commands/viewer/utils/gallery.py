'''
=======================================
EValuator: VIEWER GALLERY SCANNING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np
from dataclasses import dataclass
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import io as ioutil

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
    Returns the number of distinct non-zero label ids in a labelled MRC using mmap + np.unique
    '''
    import mrcfile

    with mrcfile.mmap(str(labelled_mrc), mode='r', permissive=True) as f:
        ids = np.unique(np.asarray(f.data))
    return int((ids != 0).sum())

def _stem_of_source_file(source_file: str) -> str:
    '''
    Returns the stem that a model MRC file refers to
    '''
    return Path(source_file).stem.removesuffix('_labelled')

def _names_in_dir(directory: Path | None, pattern: str = '*.mrc') -> frozenset[str]:
    '''
    Returns the set of filenames matching pattern in a directory, or an empty set if the directory is missing
    '''
    if directory is None or not directory.is_dir():
        return frozenset()
    return frozenset(p.name for p in directory.glob(pattern))

def _stems_from_names(names: frozenset[str], strip: tuple[str, ...] = ()) -> set[str]:
    '''
    Returns the stems of a set of *.mrc filenames, with known suffixes stripped
    '''
    stems = set()
    for name in names:
        stem = name[:-4] if name.endswith('.mrc') else name
        for suffix in strip:
            stem = stem.removesuffix(suffix)
        stems.add(stem)
    return stems

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
def scan_stage_dirs(stage_dirs: dict[str, Path | None]) -> list[ResultSet]:
    '''
    Scan stage directories and return one ResultSet per stem
    '''

    raw_d = stage_dirs.get('raw')
    seg_d = stage_dirs.get('segmentations')
    lab_d = stage_dirs.get('labelled')
    mod_d = stage_dirs.get('model')
    ana_d = stage_dirs.get('analyse')

    # Shared model results file (records keyed per stem by their source_file)
    model_results_path = _first_existing(
        *([mod_d / 'model_results.csv', mod_d / 'model_results.json'] if mod_d else []),
    )
    records_by_stem: dict[str, list[dict]] = {}
    if model_results_path:
        for record in ioutil.read_results(model_results_path)[0]:
            source_file = record.get('source_file')
            if source_file:
                records_by_stem.setdefault(_stem_of_source_file(source_file), []).append(record)

    shared_analyse = _first_existing(
        *([ana_d / 'evaluator-analyse_results.csv'] if ana_d else []),
    )

    # List each directory once; resolve per-stem paths by membership
    raw_names = _names_in_dir(raw_d)
    seg_names = _names_in_dir(seg_d)
    lab_names = _names_in_dir(lab_d)
    mod_names = _names_in_dir(mod_d)
    ana_names = _names_in_dir(ana_d, '*.csv')

    stems = sorted(
        _stems_from_names(raw_names)
        | _stems_from_names(seg_names, strip=('_seg', '_segmented'))
        | _stems_from_names(lab_names, strip=('_labelled',))
        | set(records_by_stem),
    )

    result_sets: list[ResultSet] = []
    for stem in stems:
        raw_mrc = _pick(raw_d, raw_names, f'{stem}.mrc')
        binary_mrc = _pick(seg_d, seg_names, f'{stem}.mrc', f'{stem}_seg.mrc', f'{stem}_segmented.mrc')
        labelled_mrc = _pick(lab_d, lab_names, f'{stem}_labelled.mrc', f'{stem}.mrc')
        fitted_mrc = _pick(mod_d, mod_names, 'model_fitted.mrc', f'{stem}_fitted.mrc')
        analyse_csv = shared_analyse or _pick(ana_d, ana_names, f'{stem}_analyse.csv', f'{stem}.csv')

        stem_records = records_by_stem.get(stem, [])
        has_model_output = bool(stem_records) and fitted_mrc is not None
        n_reliable = (
            sum(1 for r in stem_records if r.get('reliability', {}).get('is_reliable'))
            if stem_records else None
        )
        if stem_records:
            n_vesicles = len(stem_records)
        elif labelled_mrc is not None:
            n_vesicles = _count_labels(labelled_mrc)
        else:
            n_vesicles = 0

        result_sets.append(ResultSet(
            stem=stem,
            labelled_mrc=labelled_mrc,
            fitted_mrc=fitted_mrc if has_model_output else None,
            raw_mrc=raw_mrc,
            binary_mrc=binary_mrc,
            analyse_csv=analyse_csv,
            model_results_path=model_results_path if has_model_output else None,
            n_vesicles=n_vesicles,
            n_reliable=n_reliable,
        ))
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
