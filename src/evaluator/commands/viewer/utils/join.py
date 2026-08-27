'''
=======================================
EValuator: VIEWER ANALYSE/MODEL JOIN UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
from pathlib import Path

import pandas as pd

# ====================
# Define join function
# ====================
# join_analyse_model: returns one row per label id for the given stem, merging analyse's morphology columns with model's fit/reliability columns, plus an `include` flag column
def join_analyse_model(analyse_df: pd.DataFrame | None, model_df: pd.DataFrame | None, stem: str) -> pd.DataFrame:
    analyse_subset = (
        analyse_df[analyse_df['tomogram'].map(lambda t: Path(t).stem.removesuffix('_labelled')) == stem]
        if analyse_df is not None else pd.DataFrame()
    )
    model_subset = (
        model_df[model_df['source_file'].map(lambda s: Path(s).stem.removesuffix('_labelled')) == stem]
        if model_df is not None else pd.DataFrame()
    )
    if not analyse_subset.empty and not model_subset.empty:
        joined = analyse_subset.merge(
            model_subset, left_on='label', right_on='label_id',
            how='outer', suffixes=('_analyse', '_model'),
        )
    elif not analyse_subset.empty:
        joined = analyse_subset.copy()
    else:
        joined = model_subset.rename(columns={'label_id': 'label'}).copy()
    joined['include'] = True
    return joined.reset_index(drop=True)
