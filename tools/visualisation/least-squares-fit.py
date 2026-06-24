'''
EValuator visualisation: least squares fit

4-quadrant animation showing how a least-squares ellipsoid fit
mitigates the missing-wedge problem in cryo-ET:
---------------------------  ---------------------------
1. Tilt-series acquisition   2. Back-projected reconstruction
    (reference ellipsoid         (GENUINE missing wedge: the grey
    tilting +/-60 deg over        density is smeared / elongated
    a fixed detector below)       along the beam axis z)
---------------------------  ---------------------------
3. Fit to segmented          4. Fit vs reference
    membrane                     (recovered ellipsoid overlaid
    (true-position band          on the true ellipsoid, with a
    points with polar gaps       numeric recovery readout)
    + fitted ellipsoid)
---------------------------  ---------------------------

Quadrant 2 is the raw tomogram: unfiltered back-projection elongates density along the beam (z), so the blob is stretched and the poles smear. Segmentation (e.g. MemBrain-seg) detects the membrane at its TRUE position in the reliable equatorial band, and detects nothing at the z poles, where the membrane normal lies inside the missing wedge. Fitting a least-squares ellipsoid through those true-position band points recovers the real shape, which is exactly why the fit is robust to the missing wedge.

'''

import numpy as np, pyvista as pv
from scipy.ndimage import rotate

# =====================================================================
# Visualisation config
# =====================================================================
N = 88 # volume edge length (voxels)
DIAMETERS = (116.0, 65.0, 54.0) # reference ellipsoid diameters (dx, dy, dz)
TILT_MAX_DEG = 60.0 # acquisition half-range (+/- this)
TILT_STEP_DEG = 3.0 # tilt increment
APPLY_RAMP_FILTER = True # False = unfiltered back-projection (quadrant 2), True  = weighted back-projection
ISO_FRAC = 0.5 # isosurface threshold for quadrant 2 (frac of max)
EDGE_SOFTNESS = 1.6 # soft boundary width of the reference (voxels)

# Segmented-membrane model used for the fit (quadrants 3 and 4)
N_MEMBRANE = 500 # number of membrane points (before cap removal)
MEMBRANE_NOISE = 0.7 # segmentation jitter on those points (voxels)
FIT_MAX_FACTOR = 2.2 # reject a fit whose largest radius exceeds this * max true semi-axis (early instability)

OUTPUT = "evaluator_visualisation_least-squares-fit.mp4"
FPS = 30
WINDOW = (1600, 1000)
FRAMES_PER_TILT = 6 # acquisition smoothness
HOLD_FRAMES = 30 # pause on the finished fit
ORBIT_FRAMES = 90 # slow camera orbit at the end
CAM_DISTANCE = 8.6 # camera pull-back (higher = more zoomed out)
RNG = np.random.default_rng(0)

# Colours
C_REF = "#4ea1ff"   # reference ellipsoid (blue)
C_RECON = "#b9c2cc"   # reconstruction (grey)
C_BAND = "#ffb347"   # surviving band points (orange)
C_FIT = "#4dd07a"   # fitted ellipsoid (green)
C_AXIS = "#e8e8e8"   # tilt axis (dashed)
C_WEDGE = "#ff5566"   # missing-wedge region of the reconstruction
BG = "#0e1116"


# =====================================================================
#  Create tomogram for Q2
# =====================================================================
def make_ellipsoid_volume(n, semi_axes, softness):
    '''Soft-edged ellipsoid density centred in an n^3 volume'''
    c = (n - 1) / 2.0
    ax = np.arange(n) - c
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing='ij')
    a, b, cc = semi_axes
    r = np.sqrt((X / a) ** 2 + (Y / b) ** 2 + (Z / cc) ** 2)
    k = np.mean(semi_axes) / softness
    return (1.0 / (1.0 + np.exp((r - 1.0) * k))).astype(np.float32)

def forward_project(vol, angle_deg):
    '''Tilt the specimen by angle about y, then integrate along the beam (z)'''
    rot = rotate(vol, angle_deg, axes=(0, 2), reshape=False, order=1, mode='constant', cval=0.0)
    return rot.sum(axis=2) # 2-D detector image [x, y]

def ramp_filter(proj):
    '''1-D ramp filter along x (the tilt direction): the WBP weighting'''
    n = proj.shape[0]
    ramp = np.abs(np.fft.fftfreq(n)).reshape(-1, 1)
    return np.real(np.fft.ifft(np.fft.fft(proj, axis=0) * ramp, axis=0))

def back_project_one(proj, angle_deg, n):
    '''Smear a projection along the beam and rotate it back into the volume'''
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
    '''A dashed line as a single PolyData (used for the tilt-axis indicator)'''
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
    '''The polar caps of a reconstruction mesh that fall in the missing wedge: returns the sub-mesh whose surface normals lie within (90 - tilt_max) deg of
    the beam axis (z) which are the lowest-confidence parts of the tomogram'''
    pts = mesh.points
    if len(pts) == 0:
        return None
    r = np.linalg.norm(pts, axis=1)
    r[r == 0] = 1e-9
    cap = np.abs(pts[:, 2] / r) >= np.cos(np.deg2rad(90.0 - tilt_max_deg))
    if not cap.any():
        return None
    return mesh.extract_points(cap, adjacent_cells=True)

# =====================================================================
#  Create segmentate membrane for Q3/4
# =====================================================================
def segmented_membrane_points(semi_axes, tilt_max_deg, n_points, noise, rng):
    '''
    Membrane positions as segmentation recovers them: points lie on the TRUE ellipsoid surface, with the missing-wedge polar caps removed (apply_polar_gaps). The raw tomogram is elongated along the beam, but the membrane is detected at its true position in the reliable equatorial band and is absent at the z poles. Fitting these recovers the true shape.
    '''
    u = rng.normal(size=(n_points * 4, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True) # uniform-ish on sphere
    thresh = np.cos(np.deg2rad(90.0 - tilt_max_deg)) # cos(30 deg) ~ 0.866
    u = u[np.abs(u[:, 2]) < thresh][:n_points] # drop the polar caps
    pts = u * np.array(semi_axes) # exactly on the surface
    return pts + rng.normal(scale=noise, size=pts.shape)

def fit_ellipsoid(P):
    '''
    Algebraic least-squares ellipsoid fit (Li & Griffiths 2004 family)
    '''
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

# =====================================================================
#  Setup camera angle
# =====================================================================
def set_cameras(plotter, azimuth_deg, R):
    '''Apply the same oblique viewpoint to all four subplots'''
    el = np.deg2rad(22.0)
    az = np.deg2rad(azimuth_deg)
    D = CAM_DISTANCE * R
    focal = np.array([0.0, 0.0, -0.35 * R])
    pos = focal + D * np.array([np.cos(el) * np.cos(az),
                                np.cos(el) * np.sin(az),
                                np.sin(el)])
    cam = (tuple(pos), tuple(focal), (0, 0, 1))
    for r in range(2):
        for cidx in range(2):
            plotter.subplot(r, cidx)
            plotter.camera_position = cam


# =====================================================================
#  Precompute sequence
# =====================================================================
def precompute(semi_axes):
    ref_vol = make_ellipsoid_volume(N, semi_axes, EDGE_SOFTNESS)
    angles = np.arange(-TILT_MAX_DEG, TILT_MAX_DEG + 1e-6, TILT_STEP_DEG)
    n_ang = len(angles)

    # Quadrant 2: genuine back-projection reconstruction
    recon = np.zeros((N, N, N), np.float32)
    recon_meshes, recon_caps = [], []
    for a in angles:
        p = forward_project(ref_vol, a)
        p = ramp_filter(p) if APPLY_RAMP_FILTER else p
        recon += back_project_one(p, a, N)
        mesh = recon_to_mesh(recon, ISO_FRAC)
        recon_meshes.append(mesh)
        recon_caps.append(wedge_caps(mesh, TILT_MAX_DEG))

    # Quadrants 3 and 4: segmented membrane points, revealed progressively
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

# =====================================================================
#  Redner animation
# =====================================================================
def render():
    semi_axes = tuple(d / 2.0 for d in DIAMETERS)
    R = max(semi_axes)
    ref_vol, angles, recon_meshes, recon_caps, band_list, fits = precompute(semi_axes)
    n_ang = len(angles)

    try:
        pv.start_xvfb() # headless Linux; harmless if absent
    except Exception:
        pass

    pv.global_theme.background = BG
    pv.global_theme.font.color = "white"
    plotter = pv.Plotter(shape=(2, 2), off_screen=True, window_size=WINDOW, border=False)

    titles = ['1.  Tilt-series acquisition (+/-60 deg)',
              '2.  WBP reconstruction',
              '3.  Fit to segmented membrane (polar gaps)',
              '4.  Fit vs reference']
    for idx, (r, c) in enumerate([(0, 0), (0, 1), (1, 0), (1, 1)]):
        plotter.subplot(r, c)
        plotter.add_text(titles[idx], font_size=11, position='upper_left')

    # Q1: reference ellipsoid re-oriented each frame + fixed detector below
    plotter.subplot(0, 0)
    ref_q1 = pv.ParametricEllipsoid(*semi_axes)
    ref_actor = plotter.add_mesh(ref_q1, color=C_REF, smooth_shading=True, specular=0.3)
    det_size = 2.3 * R
    z_det = -1.8 * R
    det_plane = pv.Plane(center=(0, 0, z_det), direction=(0, 0, 1), i_size=det_size, j_size=det_size)
    # dashed tilt axis (the y axis) protruding above and below the specimen
    plotter.add_mesh(dashed_line((0, -1.7 * R, 0), (0, 1.7 * R, 0)), color=C_AXIS, line_width=2)
    plotter.add_point_labels([[0, 1.78 * R, 0]], ["tilt axis"], font_size=10, text_color=C_AXIS, show_points=False, shape=None)

    # Q4: reference as a wireframe cage so the solid fit shows through it
    plotter.subplot(1, 1)
    plotter.add_mesh(pv.ParametricEllipsoid(*semi_axes), color=C_REF, style='wireframe', line_width=1.5, opacity=0.5)
    plotter.add_text('blue cage = true   green = fit', font_size=9, position='upper_right')

    set_cameras(plotter, azimuth_deg=35.0, R=R)

    acq_frames = n_ang * FRAMES_PER_TILT
    total = acq_frames + HOLD_FRAMES + ORBIT_FRAMES
    plotter.open_movie(OUTPUT, framerate=FPS)

    dynamic = {0: [], 1: [], 2: [], 3: []}

    def clear(panel):
        for act in dynamic[panel]:
            plotter.remove_actor(act, render=False)
        dynamic[panel] = []

    true_sorted = np.sort(semi_axes)

    for f in range(total):
        in_acq = f < acq_frames
        p = min(f / max(acq_frames - 1, 1), 1.0)
        k = min(int(p * n_ang), n_ang - 1)
        tilt = -TILT_MAX_DEG + p * 2 * TILT_MAX_DEG

        # Q1: tilt series acquisition
        plotter.subplot(0, 0)
        clear(0)
        ref_actor.orientation = (0.0, tilt if in_acq else TILT_MAX_DEG, 0.0)
        proj = forward_project(ref_vol, tilt if in_acq else TILT_MAX_DEG)
        img = proj - proj.min()
        img = img / img.max() if img.max() > 0 else img
        tex = pv.numpy_to_texture(
            np.stack([(img.T * 255).astype(np.uint8)] * 3, axis=-1))
        dynamic[0].append(plotter.add_mesh(det_plane, texture=tex, show_edges=True, edge_color="#3a3f45"))
        dynamic[0].append(plotter.add_text(
            f'theta = {tilt:+.0f} deg' if in_acq else 'acquisition complete',
            font_size=10, position='lower_left', name='q1tilt'))

        # Q2: reconstruction
        plotter.subplot(0, 1)
        clear(1)
        dynamic[1].append(plotter.add_mesh(recon_meshes[k], color=C_RECON, opacity=0.55, smooth_shading=True, specular=0.2))
        if recon_caps[k] is not None:
            dynamic[1].append(plotter.add_mesh(recon_caps[k], color=C_WEDGE, opacity=0.95, smooth_shading=True))
        dynamic[1].append(plotter.add_text('red = missing-wedge region (low confidence)', font_size=9, position='lower_left', name='q2note'))

        # Q3: segmented membrane points & fitted ellipsoid
        plotter.subplot(1, 0)
        clear(2)
        band = band_list[k]
        if len(band):
            show = band if len(band) <= 280 else \
                band[RNG.choice(len(band), 280, replace=False)]
            dynamic[2].append(plotter.add_mesh(
                pv.PolyData(show), color=C_BAND,
                render_points_as_spheres=True, point_size=7))
        if fits[k] is not None:
            dynamic[2].append(plotter.add_mesh(fit_to_mesh(fits[k]), color=C_FIT, opacity=0.40, smooth_shading=True))
        dynamic[2].append(plotter.add_text('equatorial band only; poles in missing wedge', font_size=9, position='lower_left', name='q3note'))

        # Q4: fit overlaid on reference
        plotter.subplot(1, 1)
        clear(3)
        if fits[k] is not None:
            dynamic[3].append(plotter.add_mesh(fit_to_mesh(fits[k]), color=C_FIT, opacity=0.45, smooth_shading=True))
            rec = np.sort(fits[k]['radii']) * 2.0
            tru = true_sorted * 2.0
            err = 100.0 * np.abs(rec - tru) / tru
            txt = (f'recovered d (min/mid/max):\n{rec[0]:.1f} / {rec[1]:.1f} / {rec[2]:.1f}\ntrue:  {tru[0]:.1f} / {tru[1]:.1f} / {tru[2]:.1f}\nerror: {err[0]:.1f} / {err[1]:.1f} / {err[2]:.1f} %')
            dynamic[3].append(plotter.add_text(txt, font_size=9, position='lower_right', name='q4read'))

        if f >= acq_frames + HOLD_FRAMES:
            o = f - (acq_frames + HOLD_FRAMES)
            set_cameras(plotter, azimuth_deg=35.0 + 360.0 * o / ORBIT_FRAMES, R=R)

        plotter.write_frame()

    plotter.close()
    print(f'Wrote {OUTPUT}')


if __name__ == '__main__':
    render()
