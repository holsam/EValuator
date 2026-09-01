'''
=======================================
EValuator: VIEWER RESULTS PLOT BUILDERS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np, pandas as pd, plotly.graph_objects as go

# ====================
# Import internal viewer utilities
# ====================
from evaluator.commands.viewer.utils import theme as themeutil
from evaluator.commands.viewer.utils.format import pretty_column

# ====================
# Theme helpers
# ====================
ACTIVE: dict = {
    **{k: themeutil.THEMES[themeutil.DEFAULT_THEME][k] for k in ('highlight', 'base', 'reliable', 'unreliable')},
    'palette': list(themeutil.THEMES[themeutil.DEFAULT_THEME]['palette']),
    'scene_bg': '#FFFFFF', 'paper_bg': '#FFFFFF', 'grid': '#E5E5E5', 'font': '#31333F',
}


def use_theme(theme: dict) -> None:
    '''Point plot builders at resolved theme dict'''
    ACTIVE.update(theme)

# ====================
# Column / value helpers
# ====================
def find_col(df: pd.DataFrame, *needles: str) -> str | None:
    '''First column whose lower-cased name contains any needle, else None'''
    for needle in needles:
        for col in df.columns:
            if needle in col.lower():
                return col
    return None

def numeric_columns(df: pd.DataFrame) -> list[str]:
    '''Columns that hold plottable numbers'''
    skip = {'label', 'label_id', 'include', 'source_file'}
    out = []
    for col in df.columns:
        if col in skip:
            continue
        if pd.to_numeric(df[col], errors='coerce').notna().sum() >= 2:
            out.append(col)
    return out

def _labels(df: pd.DataFrame) -> np.ndarray:
    return pd.to_numeric(df['label'], errors='coerce').to_numpy()

def _point_colours(df: pd.DataFrame, selected: set[int], base) -> list:
    '''Highlight colour for selected vesicles, otherwise `base` (a scalar colour or a per-row list)'''
    labs = _labels(df)
    base_list = base if isinstance(base, (list, np.ndarray)) else [base] * len(df)
    hi = ACTIVE['highlight']
    return [hi if (not np.isnan(l) and int(l) in selected) else b for l, b in zip(labs, base_list)]

def _style(fig: go.Figure, title: str, x_title: str, y_title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        paper_bgcolor=ACTIVE['paper_bg'],
        plot_bgcolor=ACTIVE['scene_bg'],
        font_color=ACTIVE['font'],
        margin=dict(l=60, r=20, t=48, b=48),
        showlegend=False, dragmode='select',
        xaxis=dict(title=x_title, gridcolor=ACTIVE['grid'], zeroline=False),
        yaxis=dict(title=y_title, gridcolor=ACTIVE['grid'], zeroline=False)
    )
    return fig

def _axis_kwargs(series) -> dict:
    '''
    Derive scale from data (integer column with vals within 0,1 should lock to 0,1; integer columns should step as integers; column with only 1 value gets no ticks to avoid duplicates)
    '''
    s = pd.to_numeric(series, errors='coerce').dropna()
    if s.empty or s.nunique() < 2:
        return {}
    lo, hi = float(s.min()), float(s.max())
    if lo >=0 and hi <= 1:
        return {'range': [0, 1], 'dtick': 0.2}
    if bool(((s % 1) == 0).all()):
        return {'tickformat': 'd', 'dtick': max(1, int(round((hi - lo) / 6)))}
    return {}

def _apply_axes(fig: go.Figure, x=None, y=None) -> go.Figure:
    if x is not None:
        fig.update_xaxes(**_axis_kwargs(x))
    if y is not None:
        fig.update_yaxes(**_axis_kwargs(y))
    return fig

def _scatter(df, x, y, colours, hovertext=None):
    return go.Scattergl(
        x=pd.to_numeric(df[x], errors='coerce'),
        y=pd.to_numeric(df[y], errors='coerce'),
        mode='markers',
        marker=dict(size=9, color=colours, line=dict(width=0)),
        customdata=_labels(df),
        text=hovertext,
        hovertemplate='vesicle %{customdata}<br>%{x:.3g}, %{y:.3g}<extra></extra>',
    )

# ====================
# Define plot builder functions
# ====================
def feature_scatter(df: pd.DataFrame, x: str, y: str, selected: set[int]) -> go.Figure:
    fig = go.Figure(_scatter(df, x, y, _point_colours(df, selected, ACTIVE['base'])))
    _style(fig, f'{pretty_column(y)} vs {pretty_column(x)}', pretty_column(x), pretty_column(y))
     return _apply_axes(fig, x=df[x], y=df[y])

def distribution(df: pd.DataFrame, feature: str, selected: set[int], bin_size: float | None = None) -> go.Figure:
    vals = pd.to_numeric(df[feature], errors='coerce')
    hist = go.Histogram(x=vals, marker_color=ACTIVE['base'])
    if bin_size and bin_size > 0:
        hist.xbins = dict(start=0, size=bin_size)  # fixed-width bins anchored at 0: (0, w], (w, 2w], ...
    else:
        hist.nbinsx = 30
    fig = go.Figure(hist)
    labs = _labels(df)
    for l, v in zip(labs, vals):
        if not np.isnan(l) and int(l) in selected and pd.notna(v):
            fig.add_vline(x=v, line_color=ACTIVE['highlight'], line_width=2)
    _style(fig, f'{pretty_column(feature)} distribution', pretty_column(feature), 'Count')
    fig.update_xaxes(**_axis_kwargs(vals))
    fig.update_yaxes(tickformat='d')  # counts are integers
    return fig

def concordance_analyse_options(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if 'equiv_diameter' in c.lower() or 'major_axis_diameter' in c.lower()]

def concordance(df: pd.DataFrame, selected: set[int], analyse_col: str | None = None) -> go.Figure | None:
    radius = find_col(df, 'radius')
    diam = analyse_col if (analyse_col and analyse_col in df.columns) else find_col(df, 'equiv_diameter', 'major_axis_diameter')
    if radius is None or diam is None:
        return None
    work = df.copy()
    work['_model_diameter'] = pd.to_numeric(work[radius], errors='coerce') * 2
    fig = go.Figure(_scatter(work, diam, '_model_diameter', _point_colours(work, selected, ACTIVE['base'])))
    finite = pd.concat([pd.to_numeric(work[diam], errors='coerce'), work['_model_diameter']]).dropna()
    if not finite.empty:
        lo, hi = float(finite.min()), float(finite.max())
        fig.add_trace(go.Scattergl(x=[lo, hi], y=[lo, hi], mode='lines', line=dict(color=ACTIVE['grid'], dash='dash'), hoverinfo='skip'))
    _style(fig, 'Model fitted diameter vs analyse diameter', pretty_column(diam), 'Model fitted diameter (2 × radius)')
    return _apply_axes(fig, x=work[diam], y=work['_model_diameter'])

def reliability(df: pd.DataFrame, selected: set[int]) -> go.Figure | None:
    x_col = find_col(df, 'closure_fill_ratio', 'is_enclosed')
    y_col = find_col(df, 'rmse_nm', 'relative_rmse', 'rmse')
    rel_col = find_col(df, 'is_reliable')
    if x_col is None or y_col is None:
        return None
    if rel_col is not None:
        rel = df[rel_col].map(lambda v: bool(v) if pd.notna(v) else None)
        base = [ACTIVE['reliable'] if r else ACTIVE['unreliable'] for r in rel]
    else:
        base = ACTIVE['base']
    fig = go.Figure(_scatter(df, x_col, y_col, _point_colours(df, selected, base)))
    _style(fig, 'Fit RMSE vs closure', pretty_column(x_col), pretty_column(y_col))
    return _apply_axes(fig, x=df[x_col], y=df[y_col])

# ====================
# Define function to extract vesicle labels from selection
# ====================
def selected_labels_from_event(event) -> set[int]:
    '''Extract vesicle labels from Streamlit plotly_chart selection state'''
    if event is None:
        return set()
    sel = getattr(event, 'selection', None)
    if sel is None:
        try:
            sel = event['selection']
        except (TypeError, KeyError):
            return set()
    points = getattr(sel, 'points', None)
    if points is None:
        try:
            points = sel['points']
        except (TypeError, KeyError):
            return set()
    out = set()
    for p in points:
        cd = p.get('customdata')
        val = cd[0] if isinstance(cd, (list, tuple)) else cd
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            out.add(int(val))
    return out
