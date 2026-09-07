'''
=======================================
EValuator: VIEWER RESULTS PLOT BUILDERS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np, pandas as pd, plotly.graph_objects as go, scipy.stats as _stats

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
# Fit / stats helpers
# ====================
def _numeric(series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce')

def _paired_finite(x, y) -> tuple[np.ndarray, np.ndarray]:
    xf = _numeric(x).to_numpy(dtype=float)
    yf = _numeric(y).to_numpy(dtype=float)
    m = np.isfinite(xf) & np.isfinite(yf)
    return xf[m], yf[m]

def _fit_line(x, y) -> dict | None:
    '''Ordinary least-squares fit of y on x over pairwise-finite rows, or None if < 3 points or x is constant'''
    xf, yf = _paired_finite(x, y)
    if xf.size < 3 or np.ptp(xf) == 0:
        return None
    res = _stats.linregress(xf, yf)
    lo, hi = float(xf.min()), float(xf.max())
    return {
        'slope': float(res.slope), 'intercept': float(res.intercept),
        'r2': float(res.rvalue ** 2), 'n': int(xf.size),
        'x_line': [lo, hi],
        'y_line': [res.slope * lo + res.intercept, res.slope * hi + res.intercept],
    }

def fit_summary(df: pd.DataFrame, x: str, y: str) -> str | None:
    '''One-line "R^2 ...; slope ...; n ..." for a scatter, or None when it cannot be fitted'''
    fit = _fit_line(df[x], df[y])
    if fit is None:
        return None
    return f"R² {fit['r2']:.2f}; slope {fit['slope']:.3g}; n {fit['n']}"

def _annotate(fig: go.Figure, text: str) -> None:
    fig.add_annotation(
        xref='paper',
        yref='paper',
        x=0.02,
        y=0.98,
        xanchor='left',
        yanchor='top',
        text=text,
        showarrow=False,
        align='left',
        font=dict(color=ACTIVE['font'], size=12),
        bgcolor=ACTIVE['paper_bg'],
        bordercolor=ACTIVE['grid'],
        borderwidth=1,
        borderpad=4,
    )

def _trend_trace(fit: dict) -> go.Scattergl:
    return go.Scattergl(
        x=fit['x_line'],
        y=fit['y_line'],
        mode='lines',
        showlegend=False,
        line=dict(color=ACTIVE['highlight'], dash='dash'),
        hoverinfo='skip',
    )

# ====================
# Define plot builder functions
# ====================
def _colour_traces(df, x, y, selected, colour_by):
    '''Scattergl trace(s) for a feature scatter. colour_by None -> single trace; categorical
    (bool or <=6 distinct) -> one trace per level + legend; else continuous colourbar. Selected
    vesicles are always drawn on top in the highlight colour.'''
    xs, ys = _numeric(df[x]), _numeric(df[y])
    labs = _labels(df)
    hi = ACTIVE['highlight']
    sel_mask = np.array([(not np.isnan(l)) and int(l) in selected for l in labs])
    tmpl = 'vesicle %{customdata}<br>%{x:.3g}, %{y:.3g}<extra></extra>'

    if colour_by is None or colour_by not in df.columns:
        colours = [hi if s else ACTIVE['base'] for s in sel_mask]
        return [go.Scattergl(x=xs, y=ys, mode='markers', customdata=labs, hovertemplate=tmpl,
                             marker=dict(size=9, color=colours, line=dict(width=0)))]

    col = df[colour_by]
    is_cat = (col.dtype == bool) or (col.dropna().nunique() <= 6)
    if is_cat:
        pal, traces = ACTIVE['palette'], []
        for i, cat in enumerate(dict.fromkeys(col.dropna().tolist())):
            m = (col == cat).to_numpy() & ~sel_mask
            if not m.any():
                continue
            traces.append(go.Scattergl(
                x=xs[m], y=ys[m], mode='markers', name=str(cat), customdata=labs[m],
                marker=dict(size=9, color=pal[i % len(pal)], line=dict(width=0)),
                hovertemplate=f'vesicle %{{customdata}}<br>%{{x:.3g}}, %{{y:.3g}}'
                              f'<br>{pretty_column(colour_by)}: {cat}<extra></extra>',
            ))
        if sel_mask.any():
            traces.append(go.Scattergl(
                x=xs[sel_mask], y=ys[sel_mask], mode='markers', name='selected',
                customdata=labs[sel_mask], hovertemplate=tmpl,
                marker=dict(size=11, color=hi, line=dict(width=0)),
            ))
        return traces

    cvals = _numeric(col)
    out = [go.Scattergl(
        x=xs, y=ys, mode='markers', customdata=labs, hovertemplate=tmpl,
        marker=dict(size=9, color=cvals, colorscale='Viridis', line=dict(width=0),
                    colorbar=dict(title=pretty_column(colour_by))),
    )]
    if sel_mask.any():
        out.append(go.Scattergl(
            x=xs[sel_mask], y=ys[sel_mask], mode='markers', name='selected',
            customdata=labs[sel_mask], hoverinfo='skip',
            marker=dict(size=12, color=hi, line=dict(width=1, color=ACTIVE['font'])),
        ))
    return out

def feature_scatter(
    df: pd.DataFrame,
    x: str,
    y: str,
    selected: set[int], *,
    trend: bool = True,
    colour_by: str | None = None,
    log_x: bool = False,
    log_y: bool = False
) -> go.Figure:
    fig = go.Figure()
    for tr in _colour_traces(df, x, y, selected, colour_by):
        fig.add_trace(tr)
    if trend:
        fit = _fit_line(df[x], df[y])
        if fit is not None:
            fig.add_trace(_trend_trace(fit))
            _annotate(fig, f"R² {fit['r2']:.2f}; slope {fit['slope']:.3g}; n {fit['n']}")
    _style(fig, f'{pretty_column(y)} vs {pretty_column(x)}', pretty_column(x), pretty_column(y))
    fig.update_layout(showlegend=colour_by is not None)
    _apply_axes(fig, x=df[x], y=df[y])
    if log_x:
        fig.update_xaxes(type='log', autorange=True)
    if log_y:
        fig.update_yaxes(type='log', autorange=True)
    return fig

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
    fit = _fit_line(work[diam], work['_model_diameter'])
    if fit is not None:
        fig.add_trace(_trend_trace(fit))
    a, b = _paired_finite(work[diam], work['_model_diameter'])
    if a.size:
        bias = float(np.mean(b - a))
        rmse = float(np.sqrt(np.mean((b - a) ** 2)))
        slope_txt = f" · slope {fit['slope']:.3g}" if fit else ''
        _annotate(fig, f'bias {bias:+.3g}; RMSE {rmse:.3g}{slope_txt}')
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

def bland_altman(df: pd.DataFrame, col_a: str, col_b: str, selected: set[int]) -> go.Figure | None:
    '''Difference (a-b) vs mean, with bias and 95% limits of agreement.'''
    if col_a not in df.columns or col_b not in df.columns:
        return None
    a = _numeric(df[col_a]).to_numpy(dtype=float)
    b = _numeric(df[col_b]).to_numpy(dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 2:
        return None
    diff = a - b
    bias = float(np.mean(diff[m]))
    sd = float(np.std(diff[m], ddof=1))
    lo, hi = bias - 1.96 * sd, bias + 1.96 * sd
    fig = go.Figure(go.Scattergl(
        x=(a + b) / 2,
        y=diff,
        mode='markers',
        customdata=_labels(df),
        marker=dict(size=9, color=_point_colours(df, selected, ACTIVE['base']), line=dict(width=0)),
        hovertemplate='vesicle %{customdata}<br>mean %{x:.3g}, diff %{y:.3g}<extra></extra>',
    ))
    for yv, dash in ((bias, 'solid'), (lo, 'dash'), (hi, 'dash')):
        fig.add_hline(y=yv, line_color=ACTIVE['highlight'], line_dash=dash, line_width=1)
    _annotate(fig, f'bias {bias:+.3g}<br>95% limits [{lo:.3g}, {hi:.3g}]<br>n {int(m.sum())}')
    _style(fig, f'Bland-Altman: {pretty_column(col_a)} vs {pretty_column(col_b)}\nmean of {pretty_column(col_a)} & {pretty_column(col_b)}; difference (a - b)')
    return fig

def correlation_matrix(df: pd.DataFrame, cols: list[str], method: str = 'spearman') -> go.Figure:
    use = [c for c in cols if c in df.columns]
    num = df[use].apply(lambda s: pd.to_numeric(s, errors='coerce'))
    corr = num.corr(method=method)
    labels = [pretty_column(c) for c in corr.columns]
    fig = go.Figure(go.Heatmap(
        z=corr.to_numpy(),
        x=labels,
        y=labels,
        colorscale='RdBu',
        zmid=0,
        zmin=-1,
        zmax=1,
        colorbar=dict(title=method.title()),
        hovertemplate='%{x}<br>%{y}<br>r = %{z:.2f}<extra></extra>',
    ))
    fig.update_layout(
        title=f'{method.title()} correlation',
        paper_bgcolor=ACTIVE['paper_bg'],
        plot_bgcolor=ACTIVE['scene_bg'],
        font_color=ACTIVE['font'],
        margin=dict(l=120, r=20, t=48, b=120),
    )
    fig.update_xaxes(tickangle=45)
    fig.update_yaxes(autorange='reversed')
    return fig

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
