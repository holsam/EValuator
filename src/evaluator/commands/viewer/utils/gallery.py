'''
=======================================
EValuator: VIEWER GALLERY SCANNING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
from dataclasses import dataclass
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import io as ioutil
from evaluator.utils import mrc as mrcutil

# ====================
# Define dataclasses
# ====================
@dataclass
class ResultSet:
    '''
    One tomogram's processed output, under a single evaluator/ directory
    '''
    stem: str
    evaluator_dir: Path
    labelled_mrc: Path
    fitted_mrc: Path | None
    raw_mrc: Path | None            # pre-segmentation tomogram (set manually in UI)
    binary_mrc: Path | None         # pre-labelling binary segmentation (set manually in UI)
    analyse_csv: Path | None
    model_results_path: Path | None
    n_vesicles: int
    n_reliable: int | None

# ====================
# Define helper functions
# ====================
def _find_evaluator_dirs(root: Path) -> list[Path]:
    '''
    Returns every evaluator/ directory under root which has a label/ subfolder
    '''
    if root.name == 'evaluator' and (root / 'label').is_dir():
        return [root]
    return sorted({p for p in root.rglob('evaluator') if (p / 'label').is_dir()})

def _count_labels(labelled_mrc: Path) -> int:
    '''
    Returns the number of distinct non-zero label ids in a labelled MRC
    '''
    data, _ = mrcutil.readMRCFile(labelled_mrc)
    return int(len({v for v in data.reshape(-1) if v != 0}))

def _stem_of_source_file(source_file: str) -> str:
    '''
    Returns the stem that a model MRC file refers to
    '''
    return Path(source_file).stem.removesuffix('_labelled')

# ====================
# Define scan function
# ====================
def scan_result_root(root: Path) -> list[ResultSet]:
    '''
    Scan root directory for EValuator results, returning as a ResultSet
    '''
    result_sets: list[ResultSet] = []
    for evaluator_dir in _find_evaluator_dirs(root):
        label_dir = evaluator_dir / 'label'
        model_dir = evaluator_dir / 'model'
        analyse_csv = evaluator_dir / 'analyse' / 'evaluator-analyse_results.csv'
        analyse_csv = analyse_csv if analyse_csv.exists() else None

        model_results_path = next(
            (p for p in (model_dir / 'model_results.csv', model_dir / 'model_results.json') if p.exists()),
            None,
        )
        model_records = ioutil.read_results(model_results_path)[0] if model_results_path else []
        records_by_stem: dict[str, list[dict]] = {}
        for record in model_records:
            source_file = record.get('source_file')
            if source_file:
                records_by_stem.setdefault(_stem_of_source_file(source_file), []).append(record)

        fitted_mrc = model_dir / 'model_fitted.mrc'
        fitted_mrc = fitted_mrc if fitted_mrc.exists() else None

        for labelled_mrc in sorted(label_dir.glob('*_labelled.mrc')):
            stem = labelled_mrc.stem.removesuffix('_labelled')
            stem_records = records_by_stem.get(stem, [])
            has_model_output = bool(stem_records) and fitted_mrc is not None
            n_reliable = (
                sum(1 for r in stem_records if r.get('reliability', {}).get('is_reliable'))
                if stem_records else None
            )
            result_sets.append(ResultSet(
                stem=stem,
                evaluator_dir=evaluator_dir,
                labelled_mrc=labelled_mrc,
                fitted_mrc=fitted_mrc if has_model_output else None,
                raw_mrc=None,
                binary_mrc=None,
                analyse_csv=analyse_csv,
                model_results_path=model_results_path if has_model_output else None,
                n_vesicles=len(stem_records) if stem_records else _count_labels(labelled_mrc),
                n_reliable=n_reliable,
            ))
    return result_sets
