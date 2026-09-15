'''
=======================================
EValuator: VIEWER TOMOGRAM STEM UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import re

# ====================
# Known pipeline suffixes
# ====================
# Use longer suffixes first for greedy matching
STEM_SUFFIXES = (
    'model_fitted', 'model_results', 'fitted',
    'labelled', 'segmented', 'seg',
    'denoised', 'denoise',
    'filtered', 'rescaled', 'binned', 'bin',
)

# Suffixes can be separated by . or _
_STRIP_RE = re.compile(r'(?:[._](?:' + '|'.join(STEM_SUFFIXES) + r'))+$', re.IGNORECASE)

# ====================
# Define stem function
# ====================
def tomo_stem(name: str) -> str:
    '''
    Returns stem of tomogram file/path with all known suffixes removed
    '''
    stem = name.replace('\\', '/').rsplit('/', 1)[-1]
    if stem.endswith(('.mrc', '.csv', '.json')):
        stem = stem.rsplit('.', 1)[0]
    return _STRIP_RE.sub('', stem)
