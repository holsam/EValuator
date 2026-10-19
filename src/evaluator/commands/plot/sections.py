'''
=======================================
EValuator: PLOT SECTIONS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np, pandas as pd, scipy.stats as stats
from dataclasses import dataclass
from pathlib import Path

# ====================
# Import internal EValuator utilities
# ====================
from evaluator.utils.figures import plots
from evaluator.utils.settings import lg
from evaluator.commands.plot.utils import data as datautil
from evaluator.commands.plot.utils.export import write_figure, write_xlsx
from evaluator.commands.plot.utils.input import PlotRun

# ====================
# Define constant variables
# ====================
# Morphology features reported by distributions and correlations
FEATURES = ['equiv_diameter_nm', 'xy_diameter_nm', datautil.SIZE_COL, 'major_axis_diameter', 'minor_axis_diameter', 'aspect_ratio', 'eccentricity', 'membrane_volume', 'lumen_volume', 'surface_area', 'closure_fill_ratio', 'sphere_rmse_rel',]
COMPARE_FEATURES = ['equiv_diameter_nm', 'aspect_ratio', 'closure_fill_ratio', 'lumen_volume']
DIAMETERS = ['equiv_diameter_nm', 'major_axis_diameter']
DEFAULT_AGREEMENT = [('equiv_diameter_nm', datautil.SIZE_COL)]

# ====================
# Define per-run section input
# ====================
@dataclass(frozen=True)
class SectionData:
    analyse: pd.DataFrame | None
    model: pd.DataFrame | None
    joined: pd.DataFrame | None
    n_analyse_only: int = 0
    n_model_only: int = 0
    agreement: tuple[tuple[str, str], ...] = ()
    analyse_all: pd.DataFrame | None = None

def load(run: PlotRun, *, include_flagged: bool, agreement=None) -> SectionData:
    pairs = tuple(agreement or ())
    analyse = datautil.load_analyse(run.analyse_path, include_flagged=include_flagged) if run.analyse_path else None
    analyse_all = datautil.load_analyse(run.analyse_path, include_flagged=True) if run.analyse_path else None  # unfiltered, for report-both-ways stats
    model = datautil.load_model(run.model_path) if run.model_path else None
    if analyse is None or model is None:
        return SectionData(analyse, model, None, agreement=pairs, analyse_all=analyse_all)
    joined, n_analyse_only, n_model_only = datautil.join_analyse_model(analyse, model)  # before the attach below, so the joined frame keeps one model_diameter_nm
    analyse = datautil.attach_fitted_diameter(analyse, model)
    analyse_all = datautil.attach_fitted_diameter(analyse_all, model)
    return SectionData(analyse, model, joined, n_analyse_only, n_model_only, pairs, analyse_all)

# ====================
# Define sections
# ====================
def distributions(out: Path, data: SectionData, params) -> None:
    df = data.analyse
    rows = []
    for feat in FEATURES:
        if feat not in df.columns:
            continue
        width = params.bin_width_overrides.get(feat, params.bin_width)
        write_figure(plots.distribution(df, feat, set(), bin_size=width or None), out / f'{feat}_histogram.svg')
        for population, subset in datautil.populations(data.analyse_all).items():
            v = pd.to_numeric(subset[feat], errors='coerce')
            rows.append({
                'population': population, 'feature': feat, 'n': int(v.notna().sum()), 'mean': v.mean(), 'median': v.median(),
                'sd': v.std(), 'p5': v.quantile(0.05), 'p95': v.quantile(0.95),
            })
    notes = pd.DataFrame({'note': [
        'population: all = every component; vesicle_like = passes the QC filters; vesicle_like_no_z_clip = also excludes components touching a z face',
        'a conclusion that holds in all populations does not depend on the QC filter or on z clipping',
        'xy_diameter_nm is independent of z clipping; aspect_ratio, eccentricity and sphere_rmse_rel are biased low for clipped components, preferring vesicle_like_no_z_clip may be useful with caveat that excluding clipped EVs biases size small',
    ]})
    write_xlsx(out / 'summary_stats.xlsx', {'summary': pd.DataFrame(rows), 'notes': notes})

def scatter(out: Path, data: SectionData, params) -> None:
    df = data.analyse
    _log_pooling(df)
    pairs = [(_size(df, x), _size(df, y)) for x, y in params.scatter_pairs]
    tomo = datautil.aggregate_tomograms(df, list(dict.fromkeys(c for pair in pairs for c in pair if c in df.columns)), keys=('tomogram',))
    rows, tomo_rows = [], []
    for x, y in pairs:
        if x not in df.columns or y not in df.columns:
            lg.warning(f'plot | scatter: skipping {x!r} vs {y!r}, column missing')
            continue
        write_figure(plots.feature_scatter(df, x, y, set()), out / f'{x}_vs_{y}.svg')
        rows.append(_pair_stats(df, x, y))
        tomo_rows.append(_pair_stats(tomo, x, y))
    notes = pd.concat([_notes(df), pd.DataFrame({'note': [f'stats_tomogram: regression and correlation on per-tomogram medians (n = {len(tomo)} tomograms), the cluster-aware estimate; stats is pooled over EVs and descriptive only']})], ignore_index=True)
    write_xlsx(out / 'scatter_stats.xlsx', {'stats': pd.DataFrame(rows), 'stats_tomogram': pd.DataFrame(tomo_rows), 'notes': notes})

def correlations(out: Path, data: SectionData, params) -> None:
    df = data.analyse
    cols = [c for c in FEATURES if c in df.columns and pd.to_numeric(df[c], errors='coerce').notna().any()]
    if len(cols) < 2:
        raise ValueError('correlations needs at least two numeric feature columns')
    _log_pooling(df)
    tomo = datautil.aggregate_tomograms(df, cols, keys=('tomogram',))
    sheets = {}
    for method in ('spearman', 'pearson'):
        write_figure(plots.correlation_matrix(df, cols, method=method), out / f'correlation_{method}.svg', 'heatmap')
        sheets[method] = df[cols].apply(pd.to_numeric, errors='coerce').corr(method=method).reset_index(names='feature')
        sheets[f'{method}_tomogram'] = tomo[cols].corr(method=method).reset_index(names='feature')
    sheets['notes'] = pd.concat([_notes(df), pd.DataFrame({'note': [f'*_tomogram sheets: correlations of per-tomogram medians (n = {len(tomo)} tomograms), the cluster-aware estimate']})], ignore_index=True)
    write_xlsx(out / 'correlations.xlsx', sheets)

def qc(out: Path, data: SectionData, params) -> None:
    df = data.analyse
    thr = params.fill_ratio_flag_threshold
    enclosed = df['is_enclosed'].astype(float)
    low = (df['closure_fill_ratio'] < thr).groupby(df['tomogram']).sum().rename('n_flagged_low_fill')
    per = (
        df.assign(_enclosed=enclosed).groupby('tomogram')
        .agg(n_evs=('label', 'size'), pass_rate=('_enclosed', 'mean'), median_fill_ratio=('closure_fill_ratio', 'median'))
        .join(low).reset_index()
    )
    write_figure(plots.bar(per, 'tomogram', 'n_evs', title='EV count per tomogram', y_title='EVs'), out / 'count_per_tomogram.svg')
    write_figure(plots.bar(per, 'tomogram', 'pass_rate', title='Closure pass rate per tomogram', y_title='Fraction enclosed', y_range=(0, 1)), out / 'closure_pass_rate.svg')
    fig = plots.distribution(df, 'closure_fill_ratio', set(), bin_size=0.05)
    fig.add_vline(x=thr, line_dash='dash', line_color=plots.ACTIVE['font'])
    write_figure(fig, out / 'closure_fill_ratio_distribution.svg')
    write_xlsx(out / 'qc_summary.xlsx', {'summary': per})

def concordance(out: Path, data: SectionData, params) -> None:
    j = data.joined
    if j is None or j.empty:
        raise ValueError('no matching (tomogram, label) rows between analyse and model output, check both were run on the same labelled MRC(s)')
    rows = []
    for col in DIAMETERS:
        fig = plots.concordance(j, set(), analyse_col=col)
        if fig is None:
            continue
        write_figure(fig, out / f'model_vs_{col}.svg', 'square')
        a, b = _paired(j[col], j[datautil.SIZE_COL])
        diff = b - a
        rows.append({
            'analyse_measure': col, 'n': len(a), 'bias': diff.mean(), 'rmse': float(np.sqrt((diff ** 2).mean())),
            'pearson_r': a.corr(b),
        })
    match = pd.DataFrame([{'n_matched': len(j), 'n_analyse_only': data.n_analyse_only, 'n_model_only': data.n_model_only}])
    write_xlsx(out / 'concordance_stats.xlsx', {'agreement': pd.DataFrame(rows), 'matching': match})

def reliability(out: Path, data: SectionData, params) -> None:
    j = data.joined
    fig = plots.reliability(j, set()) if j is not None else None
    if fig is None:
        raise ValueError('reliability needs model rmse and analyse closure columns')
    write_figure(fig, out / 'reliability.svg')
    row = {'n': len(j)}
    rel_col = plots.find_col(j, 'is_reliable')
    if rel_col is not None:
        rel = j[rel_col].fillna(False).astype(bool)
        row |= {'n_reliable': int(rel.sum()), 'reliable_pass_rate': float(rel.mean())}
    if 'is_vesicle_like' in j.columns:
        row['n_vesicle_like'] = int(j['is_vesicle_like'].fillna(False).astype(bool).sum())
    write_xlsx(out / 'reliability_summary.xlsx', {'summary': pd.DataFrame([row])})

def agreement(out: Path, data: SectionData, params) -> None:
    j = data.joined
    if j is None or j.empty:
        raise ValueError('agreement needs matching analyse and model rows')
    rows = []
    for a, b in (data.agreement or DEFAULT_AGREEMENT):
        fig = plots.bland_altman(j, a, b, set())
        if fig is None:
            lg.warning(f'plot | agreement: skipping {a!r} vs {b!r}, column missing or fewer than two paired values')
            continue
        write_figure(fig, out / f'{a}_vs_{b}.svg')
        x, y = _paired(j[a], j[b])
        diff, sd = x - y, (x - y).std(ddof=1)
        rows.append({
            'a': a, 'b': b, 'n': len(x), 'bias': diff.mean(),
            'loa_lower': diff.mean() - 1.96 * sd, 'loa_upper': diff.mean() + 1.96 * sd,
        })
    if not rows:
        raise ValueError('agreement: no plottable measurement pair')
    write_xlsx(out / 'agreement_stats.xlsx', {'stats': pd.DataFrame(rows)})

def compare(out: Path, runs: list[PlotRun], params, *, include_flagged: bool) -> None:
    frames = []
    for r in runs:
        if not (r.analyse_path and r.group):
            continue
        df = datautil.load_analyse(r.analyse_path, include_flagged=include_flagged)
        if r.model_path:
            df = datautil.attach_fitted_diameter(df, datautil.load_model(r.model_path))
        frames.append(df.assign(sample_id=r.sample_id, group=r.group, replicate=r.replicate))
    combined = pd.concat(frames, ignore_index=True)
    feats = [_size(combined, f) for f in COMPARE_FEATURES if f in combined.columns]
    _log_pooling(combined, n_samples=combined['sample_id'].nunique())
    tomo = datautil.aggregate_tomograms(combined, feats)
    lg.info(f'plot | caveat: {datautil.tomogram_note(tomo)}')
    for feat in feats:
        write_figure(plots.group_distribution(tomo, feat), out / f'violin_{feat}.svg')
    fig = plots.pca_scatter(tomo, feats)
    if fig is not None:
        write_figure(fig, out / 'pca.svg', 'square')
    summary = tomo.groupby('group')[feats].agg(['mean', 'median'])
    summary.columns = [f'{f}_{s}' for f, s in summary.columns]
    counts = tomo.groupby('group').agg(n_tomograms=('tomogram', 'size'), n_samples=('sample_id', 'nunique'), n_evs=('n_evs', 'sum'))
    replicates = combined.groupby('group')['replicate'].nunique()
    if replicates.any():  # only when the sample sheet carries a replicate column
        counts['n_replicates'] = replicates
    notes = pd.DataFrame({'note': [datautil.tomogram_note(tomo), 'summary columns are the mean and median across per-tomogram medians']})
    write_xlsx(out / 'group_summary.xlsx', {'summary': counts.join(summary).reset_index(), 'notes': notes})
    write_xlsx(out / 'group_tests.xlsx', {'tests': _group_tests(tomo, feats), 'notes': notes})

# SECTIONS: per-run section functions, keyed by section name (compare pools every run so is called separately)
SECTIONS = {
    'distributions': distributions,
    'scatter': scatter,
    'correlations': correlations,
    'qc': qc,
    'concordance': concordance,
    'reliability': reliability,
    'agreement': agreement,
}

# ====================
# Define private helpers
# ====================
# _group_tests: tomogram-level test per feature (Mann-Whitney U for two groups, Kruskal-Wallis for more)
def _group_tests(tomo: pd.DataFrame, feats: list[str]) -> pd.DataFrame:
    rows = []
    for feat in feats:
        samples = {g: pd.to_numeric(s[feat], errors='coerce').dropna() for g, s in tomo.groupby('group')}
        samples = {g: v for g, v in samples.items() if len(v)}
        if len(samples) < 2:
            continue
        name, test = ('mann-whitney', stats.mannwhitneyu) if len(samples) == 2 else ('kruskal-wallis', stats.kruskal)
        try:
            res = test(*samples.values())
            statistic, p_value = res.statistic, res.pvalue
        except ValueError:  # e.g. every value identical
            statistic = p_value = np.nan
        rows.append({'feature': feat, 'test': name, 'statistic': statistic, 'p_value': p_value, **{f'n_tomograms_{g}': len(v) for g, v in samples.items()}})
    return pd.DataFrame(rows)

# _size: swap the shell-volume equivalent diameter for the fitted diameter when model output is available
def _size(df: pd.DataFrame, col: str) -> str:
    if col == 'equiv_diameter_nm' and datautil.SIZE_COL in df.columns and df[datautil.SIZE_COL].notna().any():
        return datautil.SIZE_COL
    return col

def _paired(a, b) -> tuple[pd.Series, pd.Series]:
    a, b = pd.to_numeric(a, errors='coerce'), pd.to_numeric(b, errors='coerce')
    m = a.notna() & b.notna()
    return a[m], b[m]

def _pair_stats(df: pd.DataFrame, x: str, y: str) -> dict:
    xs, ys = _paired(df[x], df[y])
    row = {'x': x, 'y': y, 'n': len(xs), 'pearson_r': np.nan, 'spearman_r': np.nan, 'slope': np.nan, 'slope_se': np.nan, 'r2': np.nan}
    if len(xs) >= 3 and xs.nunique() > 1:
        fit = stats.linregress(xs, ys)
        row |= {
            'pearson_r': fit.rvalue, 'spearman_r': stats.spearmanr(xs, ys).statistic,
            'slope': fit.slope, 'slope_se': fit.stderr, 'r2': fit.rvalue ** 2,
        }
    return row

def _notes(df: pd.DataFrame, n_samples: int = 1) -> pd.DataFrame:
    return pd.DataFrame({'note': [datautil.pooling_note(df, n_samples)]})

def _log_pooling(df: pd.DataFrame, n_samples: int = 1) -> None:
    lg.info(f'plot | caveat: {datautil.pooling_note(df, n_samples)}')
