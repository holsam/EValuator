'''
=======================================
EValuator: PLOT AND TABLE EXPORT
=======================================
'''

# ====================
# Import external dependencies
# ====================
import pandas as pd, plotly.graph_objects as go
from pathlib import Path

# ====================
# Define constants
# ====================
# Export size (px) per figure kind
SIZES: dict[str, tuple[int, int]] = {
    'default': (700, 480),
    'square': (560, 560),
    'wide': (900, 480),
    'heatmap': (720, 640),
}

# ====================
# Define export functions
# ====================
# check_kaleido: check if static rendering is available
def check_kaleido() -> None:
    try:
        go.Figure().to_image(format='svg')
    except Exception as e:
        raise RuntimeError(f'plot | static export needs the plot extra (kaleido) and a Chrome/Chromium install (try `plotly_get_chrome`): {e}') from e

def write_figure(fig: go.Figure, path: Path, kind: str = 'default') -> None:
    width, height = SIZES[kind]
    _vectorise(fig).write_image(path, format='svg', width=width, height=height)

def write_xlsx(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine='openpyxl') as xw:
        for name, df in sheets.items():  # first sheet is the active one, so put the main table first
            df.to_excel(xw, sheet_name=name[:31], index=False)

# ====================
# Define private helpers
# ====================
# _vectorise: scattergl traces are rasterised in SVG output, so swap them for plain scatter traces
def _vectorise(fig: go.Figure) -> go.Figure:
    out = go.Figure(fig)
    traces = []
    for tr in out.data:
        spec = tr.to_plotly_json()
        if spec.get('type') == 'scattergl':
            spec.pop('type')
            tr = go.Scatter(**spec)
        traces.append(tr)
    out.data = ()
    out.add_traces(traces)
    return out
