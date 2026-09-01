'''
=======================================
EValuator: VIEWER COLUMN-NAME FORMATTING
=======================================
'''

# Define acronyms dictionary
_ACRONYMS = {'bic': 'BIC', 'rmse': 'RMSE', 'id': 'ID', 'mrc': 'MRC', 'pca': 'PCA', 'ev': 'EV'}

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
    return s
