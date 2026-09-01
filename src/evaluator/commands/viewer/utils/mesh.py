'''
=======================================
EValuator: VIEWER MESH BUILDING UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np
import plotly.graph_objects as go
from skimage import measure

# ====================
# Define constants
# ====================

# Okabe-Ito colour-blind-safe palette
PALETTE = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7"]
MAX_SCATTER_POINTS = 25_000
OPACITY_NORMAL = 0.85
HIGHLIGHT_COLOR = "#FFD400"  # bright gold — distinct from every PALETTE entry
MIN_LABEL_VOXELS = 8  # marching_cubes needs a minimally-sized mask; smaller components are skipped, same guard as pipeline_diagram.render_volume_mesh

# ====================
# Define point-cloud trace builder
# ====================
def build_point_cloud_trace(
    data: np.ndarray,
    downsample: int = 1,
    percentile: float | None = None,
    name: str = 'points',
    colour: str = 'white',
) -> go.Scatter3d:
    '''
    Return a Scatter3d of non-zero (or percentile-thresholded voxels)
    percentile: thresholds a continuous-valued volume to its highest-density voxels as a rough structural indication
    '''
    vol = data[::downsample, ::downsample, ::downsample]
    if percentile is not None:
        threshold = np.percentile(vol, percentile)
        zz, yy, xx = np.nonzero(vol >= threshold)
    else:
        zz, yy, xx = np.nonzero(vol != 0)
    if zz.size > MAX_SCATTER_POINTS:
        rng = np.random.default_rng(0)
        keep = rng.choice(zz.size, size=MAX_SCATTER_POINTS, replace=False)
        zz, yy, xx = zz[keep], yy[keep], xx[keep]
    return go.Scatter3d(
        x=xx, y=yy, z=zz, mode='markers',
        marker=dict(size=1.5, color=colour, opacity=0.5),
        name=name, hoverinfo='name',
    )

# ====================
# Define labelled/fitted mesh trace builder
# ====================
def build_label_mesh_traces(
    labelled_or_fitted: np.ndarray,
    downsample: int = 1,
    palette: list[str] = PALETTE,
) -> dict[int, go.Mesh3d]:
    '''
    Return a marching-cubes surface per non-zero label
    '''
    vol = labelled_or_fitted[::downsample, ::downsample, ::downsample]
    label_ids = [int(v) for v in np.unique(vol) if v != 0]
    traces: dict[int, go.Mesh3d] = {}
    for i, label_id in enumerate(label_ids):
        mask = vol == label_id
        if mask.sum() < MIN_LABEL_VOXELS:
            continue
        try:
            verts, faces, _, _ = measure.marching_cubes(mask.astype(np.uint8), level=0.5)
        except (ValueError, RuntimeError):
            continue
        verts = verts[:, [2, 1, 0]]  # (Z,Y,X) array order -> (X,Y,Z) screen order
        traces[label_id] = go.Mesh3d(
            x=verts[:, 0], y=verts[:, 1], z=verts[:, 2],
            i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
            color=palette[i % len(palette)],
            opacity=OPACITY_NORMAL,
            flatshading=True,
            name=str(label_id),
            hoverinfo='name',
        )
    return traces

# ====================
# Define highlight helper
# ====================
def dim_trace(trace: go.Mesh3d, dim: bool, highlight: str = HIGHLIGHT_COLOR) -> None:
    '''Recolour a mesh: `highlight` when it is the selected one, left as-is when dimmed'''
    if not dim:
        trace.color = highlight