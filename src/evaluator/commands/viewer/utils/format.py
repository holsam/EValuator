'''
=======================================
EValuator: VIEWER COLUMN-NAME FORMATTING
=======================================
'''

# Define acronyms dictionary
_ACRONYMS = {'bic': 'BIC', 'rmse': 'RMSE', 'id': 'ID', 'mrc': 'MRC', 'pca': 'PCA', 'ev': 'EV'}

# Define dictionary of units from columns
_UNITS = {
    'membrane_volume': 'nm³',
    'lumen_volume': 'nm³',
    'radius': 'nm',
    'equiv_diameter': 'nm',
}

# Define units from column suffixes
_SUFFIX_UNITS = {
    '_deg': '°',
    '_nm3': 'nm³',
    '_nm2': 'nm²',
    '_nm': 'nm'
}

def pretty_column(name: str) -> str:
    tokens = name.replace('.', ' ').replace('_', ' ').split()
    out = []
    for tok in tokens:
        low = tok.lower()
        if low in _ACRONYMS:
            out.append(_ACRONYMS[low])
        elif low == 'nm':
            out.append('(nm)')
        else:
            out.append(tok)
    s = ' '.join(out)
    # Upper-case the first alphabetic character only; leave acronyms and the rest untouched
    for i, ch in enumerate(s):
        if ch.isalpha():
            return s[:i] + ch.upper() + s[i + 1:]
    unit = _UNITS.get(name) or next((u for suf, u in _SUFFIX_UNITS.items() if name.endswith(suf)), None)
    label = s[0].upper() + s[1:] if s and s[0].isalpha() else s
    return f'{label} ({unit})' if unit else label
