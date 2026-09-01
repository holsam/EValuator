'''
=======================================
EValuator: VIEWER COMMAND FILTERED EXPORT UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import pandas as pd
from pathlib import Path

# ====================
# Import EValuator utilities
# ====================
from evaluator.utils import paths as pathutil
from evaluator.utils.settings import lg

# ====================
# Define export function
# ====================
def export_filtered_csv(joined_df: pd.DataFrame, include_flags: dict[int, bool], source_csv: Path) -> Path:
    '''
    Writes rows of joined_df to a new CSV if include=True
    '''
    filtered = joined_df[joined_df['label'].map(include_flags).fillna(True)]
    out_path = pathutil.checkUniqueFileName(source_csv.parent, 'viewer', orig_name=source_csv.stem)
    filtered.to_csv(out_path, index=False)
    lg.info(f"viewer | exported {len(filtered)}/{len(joined_df)} filtered rows to {out_path.name}")
    return out_path
