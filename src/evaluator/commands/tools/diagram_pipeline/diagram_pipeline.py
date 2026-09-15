'''
=======================================
EValuator: PIPELINE DIAGRAM VISUALISATION SCRIPT
=======================================
'''

# ====================
# Import external dependencies
# ====================
import matplotlib.pyplot as plt, numpy, subprocess
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from pathlib import Path
from skimage import measure

# ====================
# Import internal EValuator utilities
# ====================
from evaluator.commands.tools.utils import console
from evaluator.utils import mrc as mrcutil

# ====================
# Define constants
# ====================
REPO_ROOT = Path(__file__).resolve().parents[5]
TOMOGRAM_FIXTURE = REPO_ROOT / 'tests/data/test_tomogram.mrc'
RAW_FIXTURE = REPO_ROOT / 'tests/data/test_segmentation.mrc'
CACHE_DIR = REPO_ROOT / 'out/_pipeline_diagram_cache'
# Okabe-Ito colour-blind-safe palette
PALETTE = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7']
MAX_SCATTER_POINTS = 25_000
VIEW = dict(elev=20, azim=-55)
ZOOM = 0.78

# ====================
# Define helper functions
# ====================
def _abort_diagram(msg: str):
    '''Raise an error if internal processing couldn't run'''
    console.print(f'[bold red]\\[ERROR][/] Could not generate diagram: {msg}')
    console.print_divider()
    print('\n')

def _run_evaluator(*args: str) -> None:
    subprocess.run(['uv', 'run', 'evaluator', *args], check=True, cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _ensure_pipeline_outputs(work_dir: Path) -> tuple[Path, Path]:
    '''Run the real label and model commands on the fixture MRC, caching results in work_dir, and return (labelled, fitted) paths'''
    label_out = work_dir / 'evaluator/label/test_segmentation_labelled.mrc'
    model_out = work_dir / 'evaluator/model/model_fitted.mrc'
    work_dir.mkdir(parents=True, exist_ok=True)
    if not label_out.exists():
        _run_evaluator('label', str(RAW_FIXTURE), '-o', str(work_dir))
        if not label_out.exists():
            _abort_diagram(f'{label_out} could not be created')
    if not model_out.exists():
        _run_evaluator('model', str(label_out), '-o', str(work_dir))
        if not model_out.exists():
            _abort_diagram(f'{model_out} could not be created')
    return label_out, model_out

def _make_partial_shell(shape, centre, radius, thickness, mode: str) -> numpy.ndarray:
    '''Createa a binary spherical-shell segmentation, optionally restricted to only an equatorial band or a polar cap'''
    zz, yy, xx = numpy.indices(shape)
    dist = numpy.sqrt((zz - centre[0]) ** 2 + (yy - centre[1]) ** 2 + (xx - centre[2]) ** 2)
    shell = numpy.abs(dist - radius) <= thickness / 2
    if mode == 'band':
        shell &= numpy.abs(zz - centre[0]) <= radius * 0.22
    elif mode == 'cap':
        shell &= (zz - centre[0]) >= radius * 0.25
    return shell.astype(numpy.float32)

def _ensure_synthetic_example(name: str, mode: str) -> tuple[Path, Path]:
    '''Write a synthetic partial-shell MRC and run it through label/model, caching results and returning (labelled, fitted) paths'''
    work_dir = CACHE_DIR / f'synthetic_{name}'
    seg_path = work_dir / f'{name}.mrc'
    label_out = work_dir / f'evaluator/label/{name}_labelled.mrc'
    model_out = work_dir / f'evaluator/model/model_fitted.mrc'
    work_dir.mkdir(parents=True, exist_ok=True)
    voxel_size_nm = 1.5
    shape = (48, 48, 48)
    if not seg_path.exists():
        mask = _make_partial_shell(shape, centre=(24, 24, 24), radius=16, thickness=2.5, mode=mode)
        mrcutil.writeMRCFile(mask, voxel_size_nm, seg_path)
        if not seg_path.exists():
            _abort_diagram(f'{seg_path} could not be created') 
    if not label_out.exists():
        _run_evaluator('label', str(seg_path), '-o', str(work_dir))
        if not label_out.exists():
            _abort_diagram(f'{label_out} could not be created')
    if not model_out.exists():
        _run_evaluator('model', str(label_out), '-o', str(work_dir))
        if not model_out.exists():
            _abort_diagram(f'{model_out} could not be created')
    return label_out, model_out

def _style_3d_axes(ax, shape) -> None:
    '''
    Use a black background, visible axes/ticks/grid in voxel units, Z vertical (screen z), X/Y flat (screen x/y) 
    '''
    z_extent, y_extent, x_extent = shape  # shape is (Z, Y, X) array-index order
    ax.set_facecolor('black')
    ax.set_xlim(0, x_extent)
    ax.set_ylim(0, y_extent)
    ax.set_zlim(0, z_extent)
    ax.set_box_aspect((x_extent, y_extent, z_extent), zoom=ZOOM)
    ax.set_xlabel('X (vox)', color='white', labelpad=1, fontsize=7)
    ax.set_ylabel('Y (vox)', color='white', labelpad=1, fontsize=7)
    ax.set_zlabel('Z (vox)', color='white', labelpad=1, fontsize=7)
    ax.tick_params(colors='white', labelsize=6, pad=0, length=3)
    ax.zaxis._axinfo['juggled'] = (0, 2, 1)  # keep Z axis/ticks/label together on the right edge
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.pane.set_facecolor('black')
        axis.pane.set_edgecolor('#555555')
        axis._axinfo['grid']['color'] = (1, 1, 1, 0.1)
        axis.set_major_locator(MaxNLocator(nbins=4, integer=True))  # same tick density/size across all volume extents
    ax.view_init(**VIEW)


def _render_point_cloud(ax, data: numpy.ndarray, downsample: int, percentile: float | None = None) -> None:
    '''
    Render sparse voxels as a white point cloud on a black background; percentile: thresholds a continuous-valued volume to its highest-density voxels as a rough structural indication
    '''
    vol = data[::downsample, ::downsample, ::downsample]
    if percentile is not None:
        threshold = numpy.percentile(vol, percentile)
        zz, yy, xx = numpy.nonzero(vol >= threshold)
    else:
        zz, yy, xx = numpy.nonzero(vol != 0)
    if zz.size > MAX_SCATTER_POINTS:
        rng = numpy.random.default_rng(0)
        keep = rng.choice(zz.size, size=MAX_SCATTER_POINTS, replace=False)
        zz, yy, xx = zz[keep], yy[keep], xx[keep]
    ax.scatter(xx, yy, zz, s=1.5, c='white', alpha=0.5, linewidths=0)
    _style_3d_axes(ax, vol.shape)

def _render_volume_mesh(ax, data: numpy.ndarray, downsample: int) -> int:
    '''Render each labelled component of `data` as a marching-cubes surface coloured per-label, and return the number of components rendered'''
    vol = data[::downsample, ::downsample, ::downsample]
    labels = [int(l) for l in numpy.unique(vol) if l != 0]
    n_rendered = 0
    for i, label_id in enumerate(labels):
        mask = vol == label_id
        if mask.sum() < 8:
            continue
        try:
            verts, faces, _, _ = measure.marching_cubes(mask.astype(numpy.uint8), level=0.5)
        except (ValueError, RuntimeError):
            continue
        verts = verts[:, [2, 1, 0]]  # (Z,Y,X) array order -> (X,Y,Z) screen order
        mesh = Poly3DCollection(verts[faces], alpha=0.9, linewidths=0)
        mesh.set_facecolor(PALETTE[i % len(PALETTE)])
        ax.add_collection3d(mesh)
        n_rendered += 1
    _style_3d_axes(ax, vol.shape)
    return n_rendered

def _box(ax, xy, w, h, text, facecolor, fontsize=9, sub=None):
    # Note: ax operates in a 0-1 fraction coordinate system, so boxstyle pad/rounding_size (data-unit) must be tiny relative to full-canvas units
    x, y = xy
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle='round,pad=0.004,rounding_size=0.008',
            facecolor=facecolor, edgecolor=GREY, linewidth=1.2,
        )
    )
    if sub:
        ax.text(x, y + h * 0.22, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', color='white')
        ax.text(x, y - h * 0.28, sub, ha='center', va='center', fontsize=fontsize - 2.5, color='white')
    else:
        ax.text(x, y, text, ha='center', va='center', fontsize=fontsize, fontweight='bold', color='white')

# ====================
# Define diagram rendering function
# ====================
def build_diagram(output_path: Path, downsample: int = 4) -> None:
    console.print_header('diagram', 'pipeline')

    # Create test fixture outputs if they do not already exist, and read all
    labelled_path, fitted_path = _ensure_pipeline_outputs(CACHE_DIR)
    tomogram_data, _ = mrcutil.readMRCFile(TOMOGRAM_FIXTURE)
    raw_data, _ = mrcutil.readMRCFile(RAW_FIXTURE)
    labelled_data, _ = mrcutil.readMRCFile(labelled_path)
    fitted_data, _ = mrcutil.readMRCFile(fitted_path)
    
    # Create equatorial band and apex cap examples
    band_label_path, band_fitted_path = _ensure_synthetic_example('band', 'band')
    cap_label_path, cap_fitted_path = _ensure_synthetic_example('cap', 'cap')
    
    # Initialise figure
    fig = plt.figure(figsize=(22, 22), facecolor='white')

    # Construct the first row to show the EValuator pipeline
    stage_w = 0.17
    centres = [0.14, 0.38, 0.62, 0.86]
    row1_bottom, row1_height = 0.65, 0.19
    rects = [[c - stage_w / 2, row1_bottom, stage_w, row1_height] for c in centres]

    def panel_title(centre_x: float, top_y: float, text: str, fontsize=14) -> None:
        '''Set a fixed-position figure label instead of using ax.set_title'''
        fig.text(centre_x, top_y + 0.008, text, fontsize=fontsize, fontweight='bold', ha='center', va='bottom', color='black')

    ax_tomo = fig.add_axes(rects[0], projection='3d')
    _render_point_cloud(ax_tomo, tomogram_data, downsample=downsample, percentile=97.5)
    panel_title(centres[0], row1_bottom + row1_height, 'Raw tomogram (pre-segmentation)')

    ax_raw = fig.add_axes(rects[1], projection='3d')
    _render_point_cloud(ax_raw, raw_data, downsample=downsample)
    panel_title(centres[1], row1_bottom + row1_height, 'Binary segmentation MRC')

    ax_labelled = fig.add_axes(rects[2], projection='3d')
    _render_volume_mesh(ax_labelled, labelled_data, downsample=downsample)
    panel_title(centres[2], row1_bottom + row1_height, 'Labelled MRC volume')

    ax_fitted = fig.add_axes(rects[3], projection='3d')
    _render_volume_mesh(ax_fitted, fitted_data, downsample=downsample)
    panel_title(centres[3], row1_bottom + row1_height, 'Fitted MRC volume')

    # Construct the second/third rows to show synthetic partial-coverage examples
    ex_w = 0.24
    ex_centres = [0.20, 0.50, 0.80]
    ex_height = 0.19
    example_specs = [
        ('Example: equatorial band only (missing-wedge-like data loss)', 'band', band_label_path, band_fitted_path, 0.345),
        ('Example: polar cap only (component split across two labels)', 'cap', cap_label_path, cap_fitted_path, 0.09),
    ]
    for title, mode, label_path, fitted_path_ex, row_bottom in example_specs:
        seg_mask = _make_partial_shell((48, 48, 48), (24, 24, 24), 16, 2.5, mode)
        lab_data, _ = mrcutil.readMRCFile(label_path)
        fit_data, _ = mrcutil.readMRCFile(fitted_path_ex)

        rect_seg = [ex_centres[0] - ex_w / 2, row_bottom, ex_w, ex_height]
        rect_lab = [ex_centres[1] - ex_w / 2, row_bottom, ex_w, ex_height]
        rect_fit = [ex_centres[2] - ex_w / 2, row_bottom, ex_w, ex_height]

        ax_seg = fig.add_axes(rect_seg, projection='3d')
        _render_point_cloud(ax_seg, seg_mask, downsample=1)
        panel_title(ex_centres[0], row_bottom + ex_height, 'Segmentation (synthetic)', fontsize=12)

        ax_lab = fig.add_axes(rect_lab, projection='3d')
        n_retained = _render_volume_mesh(ax_lab, lab_data, downsample=1)
        outcome = f'{n_retained} retained' if n_retained else '0 retained'
        panel_title(ex_centres[1], row_bottom + ex_height, f'After label: {outcome}', fontsize=12)

        ax_fit = fig.add_axes(rect_fit, projection='3d')
        n_fitted = _render_volume_mesh(ax_fit, fit_data, downsample=1)
        fit_outcome = f'{n_fitted} fit(s) accepted' if n_fitted else 'no reliable fit'
        panel_title(ex_centres[2], row_bottom + ex_height, f'After model: {fit_outcome}', fontsize=12)

        fig.text(ex_centres[1], row_bottom + ex_height + 0.035, title, fontsize=14, fontweight='bold', ha='center', va='bottom', color='black')

    fig.suptitle(
        f'EValuator Pipeline',
        fontsize=28, fontweight='bold', y=0.95,
    )
    fig.text(
        0.5, 0.9,
        f'Volumes rendered from {TOMOGRAM_FIXTURE.name} / {RAW_FIXTURE.name} following `evaluator model` and `evaluator analyse`.\n'
        'Raw tomogram panel is a rough density-threshold indication. Band/cap examples are synthetic, but run through `evaluator model` and `evaluator analyse`.',
        ha='center', fontsize=14, color='black', style='italic',
    )

    fig.savefig(output_path, dpi=300, facecolor='white')
    plt.close(fig)

    console.print_saved_file('Pipeline diagram saved to', output_path)
    console.print_saved_file('Cached volumes saved to', CACHE_DIR)
    console.print_divider()
    print('\n')
