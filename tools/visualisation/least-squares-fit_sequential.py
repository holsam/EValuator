'''
EValuator visualisation: least-squares fit

An animation that walks through EValuator's least squares modelling to reduce missing wedge bias.

To adjust:
  - Beat lengths: the SEG list near the bottom of render_sequential().
  - Captions: the CAPTIONS dict.
  - Layout: GROUPS split gives the scene the left two-thirds and the caption the
    right third. Widen SCENE_COLS / TEXT_COLS to change the ratio.
  - Framing: CAM_DISTANCE, and SEP (how far the fit/reference separate).
'''

# ====================
# Import external dependencies
# ====================
import numpy as np, pyvista as pv, textwrap
from scipy.ndimage import rotate
from tqdm import trange

TITLE_SEP = "\n@@\n"

# ====================
# Animation adjustable fields
# ====================
# Camera distances
CAM_DISTANCE = 7.0     # camera pull-back (x max semi-axis)
ACQ_DISTANCE = 9.0   # camera pull-back during acquisition
WIDE_DISTANCE = 10.0     # camera pull-back to frame the side-by-side pair
# Separation
SEP = 1.3     # how far the fit / reference slide apart
SIDE = 1.70     # Fourier / reconstruction offset either side of centre (x R)
# Layout: scene on the left, caption panel on the right (3 columns total)
SCENE_COLS = 2     # columns spanned by the 3-D scene
TEXT_COLS = 1     # columns for the caption panel
WRAP = 24     # caption wrap width (characters)
# Beat lengths (frames)
ENTER = 45     # ease-in / slow tilt-to-start beat
RISE = 0.40     # how far the specimen lifts during acquisition (x R)
HOLD = 48     # length of every text pause
BUILD2 = 80     # detector sweep that builds Fourier + reconstruction
SHORT = 20     # short point-clear beat
SPIN = 120     # 360 deg comparison orbit (4 s at 30 fps)
TR = 60     # short transition (acquisition -> Fourier)
BUILD = 60     # a build-up beat (reconstruction / points / fit)
TR2 = 40     # compare / overlay / return-home transitions
# Captions (to separate title from body, use TITLE_SEP
CAPTIONS = {
    "intro": "EValuator vesicle modelling"+TITLE_SEP+"Least-squares sphere/ellipsoid fitting",
    "acquire": "Tilt-series acquisition"+TITLE_SEP+"EVs imaged over tilt range of around ± 60°",
    "fourier_reconstruction": "Missing wedge and reconstruction artefacts"+TITLE_SEP+"(L) Uncollected angles leave missing wedge along the beam\n\n(R) Back-projecting with this missing wedge smears the construction along the beam.By the projection-slice theorem each tilt fills one central slice of Fourier space\n\nRed indicates the missing wedge and corresponding part of reconstruction",
    "segment": "Segmentation"+TITLE_SEP+"Membrane segmentation marks the bilayer at its true position in the reliable equatorial band which is unaffected by the missing wedge",
    "fit": "Least-squares fit modelling"+TITLE_SEP+"Points on the equatorial band are used to fit a model, mitigating the missing wedge without back-projection bias",
    "overlay": "Fit comparison"+TITLE_SEP+"The fitted ellipsoid (green) sits within the original vesicle (blue)",
}

# ====================
# Animation config
# ====================
N = 128     # volume edge length (voxels)
DIAMETERS = (116.0, 65.0, 54.0)     # reference ellipsoid diameters (dx, dy, dz)
TILT_MAX_DEG = 60.0
TILT_STEP_DEG = 3.0
APPLY_RAMP_FILTER = True
ISO_FRAC = 0.5
EDGE_SOFTNESS = 1.6
N_MEMBRANE = 500
MEMBRANE_NOISE = 0.7
FIT_MAX_FACTOR = 2.2
OUTPUT = "animation_evaluator-least-squares.mp4"
FPS = 30
WINDOW = (1600, 1000)
FRAMES_PER_TILT = 3     # acquisition pace (lower = quicker tilt series)
RNG = np.random.default_rng(0)
# Colours
C_REF = "#4ea1ff"
C_RECON = "#b9c2cc"
C_BAND = "#ffb347"
C_FIT = "#4dd07a"
C_AXIS = "#e8e8e8"
C_WEDGE = "#ff5566"
BG = "#0e1116"

# ====================
# Helper functions (volume/projection/reconstruction)
# ====================
def make_ellipsoid_volume(n, semi_axes, softness):
    c = (n - 1) / 2.0
    ax = np.arange(n) - c
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing='ij')
    a, b, cc = semi_axes
    r = np.sqrt((X / a) ** 2 + (Y / b) ** 2 + (Z / cc) ** 2)
    k = np.mean(semi_axes) / softness
    return (1.0 / (1.0 + np.exp((r - 1.0) * k))).astype(np.float32)

def forward_project(vol, angle_deg):
    rot = rotate(vol, angle_deg, axes=(0, 2), reshape=False, order=1, mode='constant', cval=0.0)
    return rot.sum(axis=2)

def ramp_filter(proj):
    n = proj.shape[0]
    ramp = np.abs(np.fft.fftfreq(n)).reshape(-1, 1)
    return np.real(np.fft.ifft(np.fft.fft(proj, axis=0) * ramp, axis=0))

def back_project_one(proj, angle_deg, n):
    smear = np.repeat(proj[:, :, None], n, axis=2)
    return rotate(smear, -angle_deg, axes=(0, 2), reshape=False, order=1, mode='constant', cval=0.0)

def make_grid(volume):
    c = (N - 1) / 2.0
    try:
        grid = pv.ImageData(dimensions=volume.shape, spacing=(1, 1, 1), origin=(-c, -c, -c))
    except AttributeError:
        grid = pv.UniformGrid(dimensions=volume.shape, spacing=(1, 1, 1), origin=(-c, -c, -c))
    grid.point_data['v'] = volume.flatten(order='F')
    return grid

def recon_to_mesh(recon, iso_frac):
    return make_grid(recon).contour([recon.max() * iso_frac], scalars='v')

def dashed_line(p0, p1, n_dash=16):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    ts = np.linspace(0.0, 1.0, n_dash * 2 + 1)
    pts, lines, idx = [], [], 0
    for i in range(0, n_dash * 2, 2):
        pts.append(p0 + (p1 - p0) * ts[i])
        pts.append(p0 + (p1 - p0) * ts[i + 1])
        lines += [2, idx, idx + 1]
        idx += 2
    poly = pv.PolyData(np.array(pts))
    poly.lines = np.array(lines)
    return poly

def wedge_caps(mesh, tilt_max_deg):
    pts = mesh.points
    if len(pts) == 0:
        return None
    r = np.linalg.norm(pts, axis=1)
    r[r == 0] = 1e-9
    cap = np.abs(pts[:, 2] / r) >= np.cos(np.deg2rad(90.0 - tilt_max_deg))
    if not cap.any():
        return None
    return mesh.extract_points(cap, adjacent_cells=True)

def membrane_band(mesh, tilt_max_deg):
    '''The equatorial band of a reconstruction mesh: everything OUTSIDE the
    missing-wedge polar caps, i.e. the part a segmentation can reliably trace.'''
    pts = mesh.points
    if len(pts) == 0:
        return None
    r = np.linalg.norm(pts, axis=1)
    r[r == 0] = 1e-9
    band = np.abs(pts[:, 2] / r) < np.cos(np.deg2rad(90.0 - tilt_max_deg))
    if not band.any():
        return None
    return mesh.extract_points(band, adjacent_cells=True)

def bp_rays_mesh(angle_deg, semi_axes, n=11, length=2.2):
    '''Parallel rays along the beam direction for one tilt, spanning the object.'''
    a = np.deg2rad(angle_deg)
    d = np.array([np.sin(a), 0.0, np.cos(a)])     # beam direction
    perp = np.array([np.cos(a), 0.0, -np.sin(a)])     # across the beam, in x-z
    R = max(semi_axes); L = length * R
    pts, lines, idx = [], [], 0
    for u in np.linspace(-1, 1, n):
        c = perp * (u * R)
        pts += [c - d * L, c + d * L]
        lines += [2, idx, idx + 1]; idx += 2
    poly = pv.PolyData(np.array(pts)); poly.lines = np.array(lines)
    return poly

# ====================
# Helper functions (segmentation/model fitting)
# ====================
def segmented_membrane_points(semi_axes, tilt_max_deg, n_points, noise, rng):
    u = rng.normal(size=(n_points * 4, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    thresh = np.cos(np.deg2rad(90.0 - tilt_max_deg))
    u = u[np.abs(u[:, 2]) < thresh][:n_points]
    pts = u * np.array(semi_axes)
    return pts + rng.normal(scale=noise, size=pts.shape)

def fit_ellipsoid(P):
    if len(P) < 9:
        return None
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    D = np.column_stack([x * x, y * y, z * z,
                         2 * x * y, 2 * x * z, 2 * y * z,
                         2 * x, 2 * y, 2 * z])
    try:
        v, *_ = np.linalg.lstsq(D, np.ones_like(x), rcond=None)
    except np.linalg.LinAlgError:
        return None
    a, b, c, d, e, f, g, h, i = v
    A = np.array([[a, d, e, g],
                  [d, b, f, h],
                  [e, f, c, i],
                  [g, h, i, -1.0]])
    try:
        centre = np.linalg.solve(-A[:3, :3], np.array([g, h, i]))
    except np.linalg.LinAlgError:
        return None
    T = np.eye(4); T[3, :3] = centre
    R = T @ A @ T.T
    R3 = R[:3, :3] / -R[3, 3]
    evals, evecs = np.linalg.eigh(R3)
    if np.any(evals <= 0):
        return None
    return dict(center=centre, radii=np.sqrt(1.0 / evals), evecs=evecs)

def reliable(fit, semi_axes):
    if fit is None:
        return None
    if np.max(fit['radii']) > FIT_MAX_FACTOR * max(semi_axes):
        return None
    return fit

def fit_to_mesh(fit):
    m = pv.ParametricEllipsoid(*fit['radii'])
    T = np.eye(4)
    T[:3, :3] = fit['evecs']
    T[:3, 3] = fit['center']
    m.transform(T, inplace=True)
    return m

# ====================
# Helper functions (Fourier space)
# ====================
def fourier_disc(angle_deg, radius):
    a = np.deg2rad(angle_deg)
    return pv.Disc(center=(0, 0, 0), inner=0.0, outer=radius,
                   normal=(np.sin(a), 0.0, np.cos(a)), r_res=1, c_res=64)

def missing_wedge_cones(radius, tilt_max_deg):
    half = np.deg2rad(90.0 - tilt_max_deg)
    hz, rr = radius * np.cos(half), radius * np.sin(half)
    up = pv.Cone(center=(0, 0, hz / 2), direction=(0, 0, -1), height=hz, radius=rr, resolution=48)
    dn = pv.Cone(center=(0, 0, -hz / 2), direction=(0, 0, 1), height=hz, radius=rr, resolution=48)
    return up.merge(dn)

# ====================
# Helper functions (precomputation)
# ====================
def precompute(semi_axes):
    ref_vol = make_ellipsoid_volume(N, semi_axes, EDGE_SOFTNESS)
    angles = np.arange(-TILT_MAX_DEG, TILT_MAX_DEG + 1e-6, TILT_STEP_DEG)
    n_ang = len(angles)
    recon = np.zeros((N, N, N), np.float32)
    recon_meshes, recon_caps = [], []
    for a in angles:
        p = forward_project(ref_vol, a)
        p = ramp_filter(p) if APPLY_RAMP_FILTER else p
        recon += back_project_one(p, a, N)
        mesh = recon_to_mesh(recon, ISO_FRAC)
        recon_meshes.append(mesh)
        recon_caps.append(wedge_caps(mesh, TILT_MAX_DEG))
    membrane = segmented_membrane_points(semi_axes, TILT_MAX_DEG, N_MEMBRANE, MEMBRANE_NOISE, RNG)
    membrane = membrane[RNG.permutation(len(membrane))]
    band_list, fits = [], []
    gate = max(2, n_ang // 3)
    for k in range(n_ang):
        n_k = int(((k + 1) / n_ang) * len(membrane))
        pts = membrane[:n_k]
        band_list.append(pts)
        fit = fit_ellipsoid(pts) if (k >= gate and n_k >= 80) else None
        fits.append(reliable(fit, semi_axes))
    return ref_vol, angles, recon_meshes, recon_caps, band_list, fits

# ====================
# Helper functions (animation)
# ====================
def ss(t):
    '''smoothstep easing in [0, 1]'''
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)

def camera_pose(az_deg, el_deg, dist, focal=(0.0, 0.0, 0.0), up=(0, 0, 1)):
    az, el = np.deg2rad(az_deg), np.deg2rad(el_deg)
    fp = np.array(focal, float)
    pos = fp + dist * np.array([np.cos(el) * np.cos(az),
                                np.cos(el) * np.sin(az),
                                np.sin(el)])
    return (tuple(pos), tuple(fp), up)

def lerp_cam(c0, c1, a):
    p0, f0, up = c0
    p1, f1, _ = c1
    p = tuple((1 - a) * x + a * y for x, y in zip(p0, p1))
    fp = tuple((1 - a) * x + a * y for x, y in zip(f0, f1))
    return (p, fp, up)

def lerp3(p0, p1, a):
    return tuple((1 - a) * x + a * y for x, y in zip(p0, p1))

def wrap(s):
    out = []
    for para in s.split('\n'):
        out.extend(textwrap.wrap(para, WRAP) if para else [''])
    return '\n'.join(out)

# ====================
# Animation rendering
# ====================
def render_sequential(sep, captions):
    semi_axes = tuple(d / 2.0 for d in DIAMETERS)
    R = max(semi_axes)
    SEP = sep * R
    FOUR_R = 1.0 * R     # Fourier-sphere radius
    det_size = 2.8 * R
    z_det = -1.6 * R
    ref_vol, angles, recon_meshes, recon_caps, band_list, fits = precompute(semi_axes)
    recon_band = membrane_band(recon_meshes[-1], TILT_MAX_DEG)
    print(f'\tPrecomputed animation geometries')
    n_ang = len(angles)
    # last reliable fit drives the fit / compare / overlay beats
    fit_final = next((fits[i] for i in range(len(fits) - 1, -1, -1) if fits[i] is not None), None)
    if fit_final is None:
        raise RuntimeError("No reliable fit was produced; relax FIT_MAX_FACTOR or add points.")
    print(f'\tFound last reliable fit')
    # static meshes reused every frame
    REF = pv.ParametricEllipsoid(*semi_axes)
    FITM = fit_to_mesh(fit_final)
    DET = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), i_size=det_size, j_size=det_size)
    DETC = pv.Plane(center=(0, 0, 0), direction=(0, 0, 1), i_size=2 * FOUR_R, j_size=2 * FOUR_R)
    AXIS = dashed_line((0, -1.7 * R, 0), (0, 1.7 * R, 0), n_dash=40)
    FS = pv.Sphere(radius=FOUR_R)
    WEDGE = missing_wedge_cones(FOUR_R, TILT_MAX_DEG)
    FDISCS = [fourier_disc(a, FOUR_R) for a in angles]
    print(f'\tCreated static meshes')
    # recovery readout text (for the compare hold)
    rec = np.sort(fit_final['radii']) * 2.0
    tru = np.sort(semi_axes) * 2.0
    err = 100.0 * np.abs(rec - tru) / tru
    recovery_txt = ("Recovered vs true diameter (voxels)\n\n"
                    f"min:  {rec[0]:.1f}  /  {tru[0]:.1f}   ({err[0]:.1f}%)\n"
                    f"mid:  {rec[1]:.1f}  /  {tru[1]:.1f}   ({err[1]:.1f}%)\n"
                    f"max:  {rec[2]:.1f}  /  {tru[2]:.1f}   ({err[2]:.1f}%)")
    CAPTIONS = captions
    CAPTIONS.update({
        "fourier_recon_hold": CAPTIONS.get("fourier_reconstruction"),
        "segment_hold": CAPTIONS.get("segment"),
        "fit_hold": CAPTIONS.get("fit"),
        "compare_apart": CAPTIONS.get("overlay"),
        "compare_hold": CAPTIONS.get("overlay"),
        "compare_spin": recovery_txt,
        "outro": recovery_txt,
    })
    print(f'\tSet beat captions')
    # define animation timeline
    SEG = [
        ("intro",             "hold",   HOLD),
        ("enter_acquire",     "motion", ENTER),
        ("acquire",           "motion", n_ang * FRAMES_PER_TILT),
        ("to_fourier",        "motion", TR2),
        ("detector_hold",     "hold",   HOLD),
        ("build_fourier",     "motion", BUILD2),
        ("fourier_recon_hold","hold",   HOLD),
        ("zoom_to_recon",     "motion", TR2),
        ("segment",           "motion", BUILD),
        ("segment_hold",      "hold",   HOLD),
        ("fit",               "motion", BUILD),
        ("fit_hold",          "hold",   HOLD),
        ("clear_points",      "motion", SHORT),
        ("compare_apart",     "motion", TR2),
        ("compare_hold",      "hold",   HOLD),
        ("overlay",           "motion", TR2),
        ("compare_spin",      "motion", SPIN),
        ("outro",             "hold",   HOLD),
    ]
    starts, acc = [], 0
    for _, _, fr in SEG:
        starts.append(acc); acc += fr
    total = acc
    print(f'\tDefined animation timeline')
    def locate(f):
        for i, (nm, kd, fr) in enumerate(SEG):
            if f < starts[i] + fr:
                return nm, kd, min((f - starts[i]) / max(fr - 1, 1), 1.0)
        return SEG[-1][0], SEG[-1][1], 1.0
    # headless setup
    try:
        pv.start_xvfb()
    except Exception:
        pass
    pv.global_theme.background = BG
    pv.global_theme.font.color = "white"

    ncols = SCENE_COLS + TEXT_COLS
    plotter = pv.Plotter(shape=(1, ncols), groups=[(0, np.s_[0:SCENE_COLS])], off_screen=True, window_size=WINDOW, border=False)
    SCENE = (0, 0)     # grouped left block
    PANEL = (0, SCENE_COLS)     # first ungrouped column on the right
    print(f'\tInitialised animation plotter')
    # camera poses
    HOME = camera_pose(35, 18, CAM_DISTANCE * R)
    ACQ_CAM = camera_pose(35, 16, ACQ_DISTANCE * R, focal=(0, 0, -0.25 * R))
    WIDE = camera_pose(35, 18, WIDE_DISTANCE * R)
    def camera_for(name, t):
        a = ss(t)
        if name == "enter_acquire":
            return lerp_cam(HOME, ACQ_CAM, a)
        if name in ("acquire", "acquire_hold"):
            return ACQ_CAM
        if name == "to_fourier":
            return lerp_cam(ACQ_CAM, WIDE, a)
        if name in ("detector_hold", "build_fourier", "fourier_recon_hold"):
            return WIDE
        if name == "zoom_to_recon":
            return lerp_cam(WIDE, HOME, a)
        if name == "compare_spin":
            return camera_pose(35 + 360 * a, 18, CAM_DISTANCE * R)
        return HOME
    print(f'\tSet up camera poses')
    # clear animation
    dyn = []
    def clear():
        for a in dyn:
            plotter.remove_actor(a, render=False)
        dyn.clear()

    # per-object helpers
    def set_caption(text):
        for nm in ("cap_title", "cap_body"):
            plotter.remove_actor(nm, render=False)
        if not text:
            return
        if TITLE_SEP in text:
            title, body = text.split(TITLE_SEP, 1)
        else:
            title, body = "", text
        has_title = bool(title.strip())
        if has_title:
            ta = plotter.add_text(wrap(title), name="cap_title", position=(0.06, 0.58), viewport=True, font_size=16, color="white")
            tp = ta.GetTextProperty()
            tp.SetBold(True); tp.SetJustificationToLeft()
            tp.SetVerticalJustificationToBottom()
        ba = plotter.add_text(wrap(body), name="cap_body", position=(0.06, 0.52 if has_title else 0.50), viewport=True, font_size=13, color="#cfd6dd")
        bp = ba.GetTextProperty()
        bp.SetJustificationToLeft()
        if has_title:
            bp.SetVerticalJustificationToTop()
        else:
            bp.SetVerticalJustificationToCentered()
        
    def add_ref(pos=(0, 0, 0), opacity=1.0, wireframe=False, orient=(0, 0, 0)):
        if opacity <= 0.01:
            return
        a = plotter.add_mesh(REF, color=C_REF, style='wireframe' if wireframe else 'surface', opacity=opacity, smooth_shading=not wireframe, line_width=1.5 if wireframe else 1.0, specular=0.3, reset_camera=False)
        a.position = pos
        a.orientation = orient
        dyn.append(a)

    def add_detector(tilt, pos=(0,0,z_det), opacity=1.0):
        if opacity <= 0.01:
            return
        proj = forward_project(ref_vol, tilt)
        img = proj - proj.min()
        img = img / img.max() if img.max() > 0 else img
        tex = pv.numpy_to_texture(np.stack([(img.T * 255).astype(np.uint8)] * 3, axis=-1))
        a = plotter.add_mesh(DET, texture=tex, opacity=opacity, show_edges=True, edge_color='#3a3f45', reset_camera=False)
        a.position = pos
        dyn.append(a)
    
    def add_detector_sweep(pos, tilt, opacity):
        if opacity <= 0.01:
            return
        proj = forward_project(ref_vol, tilt)
        img = proj - proj.min()
        img = img / img.max() if img.max() > 0 else img
        tex = pv.numpy_to_texture(np.stack([(img.T * 255).astype(np.uint8)] * 3, axis=-1))
        a = plotter.add_mesh(DETC, texture=tex, opacity=opacity, reset_camera=False)
        a.position = pos
        a.orientation = (0, tilt, 0)     # plane normal tracks the central-slice normal
        dyn.append(a)

    def add_axis(opacity=1.0, z=0.0):
        if opacity <= 0.01:
            return
        a = plotter.add_mesh(AXIS, color=C_AXIS, line_width=1.5, opacity=opacity, reset_camera=False)
        a.position = (0, 0, z)
        dyn.append(a)

    def add_signal_points(pts, pos=(0, 0, 0), opacity=1.0):
        if opacity <= 0.01 or len(pts) == 0:
            return
        show = pts if len(pts) <= 320 else pts[RNG.choice(len(pts), 320, replace=False)]
        a = plotter.add_mesh(pv.PolyData(show), color='#9fc2ff', render_points_as_spheres=True,
                             point_size=5, opacity=opacity, reset_camera=False)
        a.position = pos; dyn.append(a)

    def add_bp_rays(angle_deg, pos=(0, 0, 0), opacity=0.22):
        a = plotter.add_mesh(bp_rays_mesh(angle_deg, semi_axes), color='#5fa8ff',
                             line_width=1, opacity=opacity, reset_camera=False)
        a.position = pos; dyn.append(a)

    def add_fourier(pos=(0, 0, 0), opacity=1.0, n_slices=None):
        if opacity <= 0.01:
            return
        a = plotter.add_mesh(FS, style='wireframe', color='#5a6678', opacity=0.65 * opacity, line_width=1, reset_camera=False)
        a.position = pos; dyn.append(a)
        w = plotter.add_mesh(WEDGE, color=C_WEDGE, opacity=0.45 * opacity, smooth_shading=True, reset_camera=False)
        w.position = pos; dyn.append(w)
        for j in range(min(n_ang if n_slices is None else n_slices, n_ang)):
            d = plotter.add_mesh(FDISCS[j], color='#9fc2ff', opacity=0.30 * opacity, show_scalar_bar=False, reset_camera=False)
            d.position = pos; dyn.append(d)

    def add_recon(k, opacity, cap_opacity, pos=(0, 0, 0)):
        if opacity > 0.01:
            a = plotter.add_mesh(recon_meshes[k], color=C_RECON, opacity=opacity, smooth_shading=True, specular=0.2, reset_camera=False)
            a.position = pos; dyn.append(a)
        if cap_opacity > 0.01 and recon_caps[k] is not None:
            c = plotter.add_mesh(recon_caps[k], color=C_WEDGE, opacity=cap_opacity, smooth_shading=True, reset_camera=False)
            c.position = pos; dyn.append(c)

    def add_band_wireframe(opacity):
        if opacity <= 0.01 or recon_band is None:
            return
        a = plotter.add_mesh(recon_band, style='wireframe', color='white',
                             opacity=opacity, line_width=1, reset_camera=False)
        dyn.append(a)

    def add_points(pts, opacity):
        if opacity <= 0.01 or len(pts) == 0:
            return
        show = pts if len(pts) <= 280 else pts[RNG.choice(len(pts), 280, replace=False)]
        a = plotter.add_mesh(pv.PolyData(show), color=C_BAND, render_points_as_spheres=True, point_size=7, opacity=opacity, reset_camera=False)
        dyn.append(a)

    def add_fit(pos=(0, 0, 0), opacity=0.55, scale=1.0):
        if opacity <= 0.01:
            return
        a = plotter.add_mesh(FITM, color=C_FIT, opacity=opacity, smooth_shading=True, reset_camera=False)
        a.position = pos
        a.scale = (scale, scale, scale)
        dyn.append(a)
    print(f'\tCreated component helpers')
    # draw a frame
    def draw(name, t):
        s = ss(t)
        last = n_ang - 1

        if name == "intro":
            add_ref(opacity=1.0)

        elif name == "enter_acquire":
            z = RISE * R * s
            add_ref(pos=(0, 0, z), orient=(0, -TILT_MAX_DEG * s, 0))
            appear = ss(max((t - 0.4) / 0.6, 0.0))     # detector/axis arrive later
            add_detector(tilt=-TILT_MAX_DEG * s, opacity=appear)
            add_axis(opacity=appear, z=z)

        elif name == "acquire":
            tilt = -TILT_MAX_DEG + s * 2 * TILT_MAX_DEG
            add_ref(pos=(0, 0, RISE * R), orient=(0, tilt, 0))
            add_detector(tilt=tilt)
            add_axis(z=RISE*R)

        elif name == "acquire_hold":
            add_ref(pos=(0, 0, RISE * R), orient=(0, TILT_MAX_DEG, 0))
            add_detector(tilt=TILT_MAX_DEG)
            add_axis(z=RISE*R)

        elif name == "to_fourier":
            # specimen recedes; the detector lifts to the Fourier side and becomes the focus
            ref_fade = 1.0 - ss(min(t / 0.5, 1.0))     # gone by the midpoint
            add_ref(pos=(0, 0, RISE * R), opacity=ref_fade, orient=(0, TILT_MAX_DEG, 0))
            add_axis(opacity=ref_fade, z=RISE * R)
            move = ss(max((t - 0.5) / 0.5, 0.0))     # only moves in the second half
            det_pos = lerp3((0, 0, z_det), (-SIDE * R, 0, 0), move)
            add_detector(tilt=0.0, pos=det_pos, opacity=1.0)

        elif name == "detector_hold":
            add_detector_sweep(tilt=0.0, pos=(-SIDE * R, 0, 0), opacity=1.0)

        elif name == "build_fourier":
            k = int(s * (n_ang - 1))
            theta = -TILT_MAX_DEG + s * 2 * TILT_MAX_DEG
            # the projected signal back-projects and accumulates; poles stay empty
            add_detector(tilt=0.0, pos=(SIDE * R, 0, 0), opacity=0.5 * (1.0 - s))
            add_bp_rays(theta, pos=(SIDE * R, 0, 0))
            add_signal_points(band_list[k], pos=(SIDE * R, 0, 0))
            # the reconstruction surface that results, with its red polar caps
            add_recon(k, opacity=0.7 * s, cap_opacity=0.95 * s, pos=(-SIDE * R, 0, 0))

        elif name == "fourier_recon_hold":
            add_signal_points(band_list[-1], pos=(SIDE * R, 0, 0))
            add_recon(n_ang - 1, opacity=0.7, cap_opacity=0.95, pos=(-SIDE * R, 0, 0))

        elif name == "zoom_to_recon":
            shift_x = SIDE * R * s
            add_signal_points(band_list[-1], pos=(SIDE * R + shift_x, 0, 0), opacity=1.0 - s)
            add_recon(n_ang - 1, opacity=0.7, cap_opacity=0.95, pos=(-SIDE * R + shift_x, 0, 0))

        elif name == "segment":
            # grey reconstruction and red caps fade out; the band is traced as a membrane
            add_recon(n_ang - 1, opacity=0.7 * (1.0 - s), cap_opacity=0.95 * (1.0 - s))
            add_band_wireframe(opacity=s)

        elif name == "segment_hold":
            add_band_wireframe(opacity=1.0)

        elif name == "fit":
            add_band_wireframe(opacity=0.8)     # segmentation stays
            add_points(band_list[-1], opacity=s)
            add_fit(opacity=0.55 * s, scale=1.0)     # ellipsoid grows through it

        elif name == "fit_hold":
            add_band_wireframe(opacity=0.8)
            add_points(band_list[-1], opacity=1.0)
            add_fit(opacity=0.55, scale=1.0)

        elif name == "clear_points":
            add_fit(opacity=0.55, scale=1.0)
            add_band_wireframe(opacity=0.8 * (1.0 - s))

        elif name == "compare_apart":
            drift = SEP * R * s
            add_fit(pos=(drift, 0, 0), opacity=0.55)     # 0 -> +SEP
            ref_in = ss(max((t - 0.2) / 0.8, 0.0))     # fades in after it enters
            add_ref(pos=(-2 * SEP * R + drift, 0, 0), opacity=0.55 * ref_in)     # -2SEP -> -SEP

        elif name == "compare_hold":
            add_fit(pos=(SEP, 0, 0), opacity=0.55)
            add_ref(pos=(-SEP, 0, 0), opacity=0.55)

        elif name == "overlay":
            off = SEP * (1.0 - s)
            add_fit(pos=(off, 0, 0), opacity=0.55)
            if s > 0.5:
                add_ref(pos=(-off, 0, 0), opacity=0.9, wireframe=True)
            else:
                add_ref(pos=(-off, 0, 0), opacity=0.55)

        elif name == "compare_spin":
            add_fit(opacity=0.55)
            add_ref(opacity=0.9, wireframe=True)

        elif name == "outro":
            add_fit(opacity=0.55 * (1.0 - s))
            add_ref(opacity=0.9, wireframe=True)
            
    # render animation
    print(f'\tStarting rendering (total={total})')
    plotter.open_movie(OUTPUT, framerate=FPS)
    for f in trange(total, desc = 'Frames rendered'):
        name, kind, t = locate(f)
        plotter.subplot(*SCENE)
        clear()
        draw(name, t)
        plotter.camera_position = camera_for(name, t)
        plotter.subplot(*PANEL)
        cap = set_caption(CAPTIONS.get(name,""))
        plotter.add_text(cap, name="cap", position="upper_left", font_size=14, color="white")
        plotter.write_frame()
    plotter.close()
    print(f"\tWrote {OUTPUT}  ({total} frames, {total / FPS:.1f} s)")

if __name__ == "__main__":
    print(f'\nCreating visualisation: least-squares fit (sequential)')
    render_sequential(sep=SEP, captions=CAPTIONS)