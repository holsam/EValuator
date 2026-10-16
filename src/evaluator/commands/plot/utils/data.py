'''
=======================================
EValuator: PLOT DATA PREPROCESSING
=======================================
'''

# ====================
# Import external dependencies
# ====================
import pandas as pd
from pathlib import Path

# ====================
# Import internal EValuator utilities
# ====================
from evaluator.utils import io as ioutil
from evaluator.utils.settings import lg

# ====================
# Define constant variables
# ====================
ANALYSE_REQUIRED = ['tomogram', 'label', 'equiv_diameter_nm', 'major_axis_diameter', 'minor_axis_diameter', 'aspect_ratio', 'eccentricity', 'membrane_volume', 'lumen_volume', 'surface_area', 'is_enclosed', 'closure_fill_ratio']
MODEL_REQUIRED = ['label_id', 'source_file', 'chosen_model', 'radius', 'rmse_nm']

# ====================
# Define loaders
# ====================
def load_analyse(path: Path, *, include_flagged: bool = False) -> pd.DataFrame:
    df = pd.read_csv(path)
    _validate(df, ANALYSE_REQUIRED, path.name)
    if include_flagged or 'is_vesicle_like' not in df.columns:  # older csvs predate the column: nothing to filter
        return df
    keep = df['is_vesicle_like'].fillna(False).astype(bool)
    dropped = df[~keep]
    if len(dropped):
        lg.info(f'plot | {path.name}: excluded {len(dropped)}/{len(df)} component(s) flagged as not vesicle-like (is_vesicle_like == False)')
        _log_drop_reasons(dropped)
    return df[keep].reset_index(drop=True)

def load_model(path: Path) -> pd.DataFrame:
    records, _ = ioutil.read_results(path)
    df = pd.json_normalize(records)  # flattens nested reliability / fit dicts to 'reliability.is_reliable' etc.
    _validate(df, MODEL_REQUIRED, path.name)
    df['model_diameter_nm'] = pd.to_numeric(df['radius'], errors='coerce') * 2
    return df

# join_analyse_model: inner join on (tomogram basename, label); also returns the unmatched counts on each side
def join_analyse_model(analyse: pd.DataFrame, model: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    model = model.assign(tomogram=model['source_file'].map(lambda s: Path(s).name))
    joined = analyse.merge(model, left_on=['tomogram', 'label'], right_on=['tomogram', 'label_id'], how='inner', suffixes=('', '_model'))
    return joined, len(analyse) - len(joined), len(model) - len(joined)

# pooling_note: caveat text for any statistic that treats pooled EVs as independent observations
def pooling_note(df: pd.DataFrame, n_samples: int = 1) -> str:
    return (f'n = {len(df)} EVs pooled across {df["tomogram"].nunique()} tomogram(s) and {n_samples} sample(s); EVs are treated as independent and no clustering-adjusted test is applied, so treat statistics as descriptive only')

# ====================
# Define private helpers
# ====================
def _validate(df: pd.DataFrame, required: list[str], name: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f'{name}: input missing required column(s): {", ".join(missing)}')

def _log_drop_reasons(dropped: pd.DataFrame) -> None:
    if 'qc_flags' not in dropped.columns:
        return
    # qc_flags is comma-separated, so a component with two flags counts once under each
    flags = dropped['qc_flags'].dropna().astype(str).str.split(',').explode().str.strip()
    counts = flags[flags != ''].value_counts()
    if not counts.empty:
        lg.info('plot |   by reason: ' + ', '.join(f'{reason}={n}' for reason, n in counts.items()))
