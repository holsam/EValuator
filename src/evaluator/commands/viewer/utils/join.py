'''
=======================================
EValuator: VIEWER ANALYSE/MODEL JOIN UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import pandas as pd

# ====================
# Import EValuator viewer utilities
# ====================
from evaluator.commands.viewer.utils.stems import tomo_stem

# ====================
# Define join function
# ====================
# join_analyse_model: returns one row per label id for the given stem, merging analyse's morphology columns with model's fit/reliability columns
def join_analyse_model(analyse_df: pd.DataFrame | None, model_df: pd.DataFrame | None, stem: str) -> tuple[pd.DataFrame, set[str], set[str]]:
    analyse_subset = (
        analyse_df[analyse_df['tomogram'].map(tomo_stem) == stem]
        if analyse_df is not None else pd.DataFrame()
    )
    model_subset = (
        model_df[model_df['source_file'].map(tomo_stem) == stem]
        if model_df is not None else pd.DataFrame()
    )
    a_src = set(analyse_subset.columns)
    m_src = set(model_subset.columns)
    shared = a_src & m_src  # pick up _analyse / _model suffixes in the merge
    if not analyse_subset.empty and not model_subset.empty:
        joined = analyse_subset.merge(
            model_subset, left_on='label', right_on='label_id',
            how='outer', suffixes=('_analyse', '_model'),
        )
    elif not analyse_subset.empty:
        joined = analyse_subset.copy()
    else:
        joined = model_subset.rename(columns={'label_id': 'label'}).copy()
    m_src.discard('label_id')
    m_src.add('label')
    joined['include'] = True
    joined = joined.reset_index(drop=True)
    analyse_names: set[str] = set()
    model_names: set[str] = set()
    for c in joined.columns:
        if c == 'include':
            continue
        if c.endswith('_model') or (c in m_src and c not in shared and c not in a_src):
            model_names.add(c)
        else:
            analyse_names.add(c)
    if 'label' in joined.columns:
        analyse_names.add('label')
        model_names.add('label')
    return joined, analyse_names, model_names
