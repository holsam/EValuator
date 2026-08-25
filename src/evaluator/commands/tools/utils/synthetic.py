'''
=======================================
EValuator: SYNTHETIC EV UTILITY FUNCTIONS
=======================================
Functions for generating synthetic EVs
'''

# ====================
# Import external dependencies
# ====================
import numpy as np

# ====================
# generate_ev_shell: returns boolean array (Z,Y,X) and dictionary of true parameters
# ====================
def generate_ev_shell(
    diameter_nm: float,
    thickness_nm: float = 5.0,
    voxel_size_nm: float = 2.0,
    box_padding_voxels: int = 10,
    centre_offset_voxels: tuple[float, float, float] = (0.0, 0.0, 0.0),
    axis_ratios: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> tuple[np.ndarray, dict]:
    '''
    Generate a synthetic EV shell as a binary volume
    '''
    radius_voxels = diameter_nm / (2 * voxel_size_nm)
    half_thickness_voxels = thickness_nm / (2 * voxel_size_nm)
    box_size = int(np.ceil(2 * radius_voxels * max(axis_ratios) + 2 * box_padding_voxels))
    centre = np.array([box_size / 2 + o for o in centre_offset_voxels])
    z, y, x = np.indices((box_size, box_size, box_size)).astype(float)
    dz = (z - centre[0]) / axis_ratios[0]
    dy = (y - centre[1]) / axis_ratios[1]
    dx = (x - centre[2]) / axis_ratios[2]
    dist = np.sqrt(dz ** 2 + dy ** 2 + dx ** 2)
    shell = np.abs(dist - radius_voxels) <= half_thickness_voxels

    truth = {
        "diameter_nm": diameter_nm,
        "thickness_nm": thickness_nm,
        "centre_voxels": centre,
        "voxel_size_nm": voxel_size_nm,
        "box_size_voxels": box_size,
        "axis_ratios": axis_ratios,
        "shell_voxels_truth": int(shell.sum()),
    }
    return shell, truth

# ====================
# apply_polar_gaps: returns boolean array derived from input shell with polar voxels removed (nb fast geometric proxy for missing-wedge polar caps, is deterministic for unit testing)
# ====================
def apply_polar_gaps(shell: np.ndarray, gap_half_angle_deg: float = 30.0) -> np.ndarray:
    '''
    Remove voxels whose radial normal is within ``gap_half_angle_deg`` of Z
    '''
    coords = np.argwhere(shell).astype(float)
    if len(coords) == 0:
        return np.zeros_like(shell)
    centre = np.array(shell.shape) / 2
    normals = coords - centre
    norms = np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    normals = normals / norms
    z_alignment = np.abs(normals[:, 0])
    cos_threshold = np.cos(np.deg2rad(90 - gap_half_angle_deg))
    keep = z_alignment < cos_threshold
    out = np.zeros_like(shell, dtype=bool)
    kept = coords[keep].astype(int)
    out[kept[:, 0], kept[:, 1], kept[:, 2]] = True
    return out

# ====================
# apply_fourier_missing_wedge: returns boolean array with Fourier-space degradation to mimic missing wedge (tilt_range_deg = tilt-series half-range (i.e ±60° tilt series has half-range 60°); threshold = re-binarisation threshold for inverse-FFT magnitude relative to maximum)
# ====================
def apply_fourier_missing_wedge(
    volume: np.ndarray,
    tilt_range_deg: float = 60.0,
    threshold: float = 0.3,
) -> np.ndarray:
    '''
    Apply a Fourier-space missing wedge, assuming tilt around the Y axis
    '''
    vol = volume.astype(float)
    f = np.fft.fftshift(np.fft.fftn(vol))
    nz, ny, nx = vol.shape
    kz_idx = np.arange(nz) - nz / 2
    kx_idx = np.arange(nx) - nx / 2
    KZ, _, KX = np.meshgrid(kz_idx, np.arange(ny), kx_idx, indexing="ij")
    angle = np.arctan2(np.abs(KZ), np.abs(KX) + 1e-12)
    sampled = angle <= np.deg2rad(tilt_range_deg)
    f_masked = f * sampled
    reconstructed = np.real(np.fft.ifftn(np.fft.ifftshift(f_masked)))
    reconstructed = np.clip(reconstructed, 0, None)
    return reconstructed > (threshold * reconstructed.max())

# ====================
# _rotate_to_pole: returns ndarray of points generated around +z rotated so +z maps onto unit vector pole
# ====================
def _rotate_to_pole(points: np.ndarray, pole: np.ndarray) -> np.ndarray:
    pole = pole / np.linalg.norm(pole)
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(z, pole)
    sin_angle = np.linalg.norm(axis)
    cos_angle = np.dot(z, pole)
    if sin_angle < 1e-12:
        return points if cos_angle > 0 else points * np.array([1.0, -1.0, -1.0])
    axis /= sin_angle
    K = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0],
    ])
    R = np.eye(3) + K * sin_angle + K @ K * (1 - cos_angle)
    return points @ R.T

# ====================
# generate_full_sphere_points: returns tuple of ndarray of points uniformly sampled on a full sphere shell and dictionary of true parameters
# ====================
def generate_full_sphere_points(
    radius_nm: float,
    centre: tuple[float, float, float] = (0.0, 0.0, 0.0),
    n: int = 500,
    seed: int | None = None,
) -> tuple[np.ndarray, dict]:
    '''
    Uniformly sample n points on a full sphere shell, used as the shared anchor case for both the polar-cap and equatorial-band completeness sweeps
    '''
    rng = np.random.default_rng(seed)
    vecs = rng.normal(size=(n, 3))
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    points = vecs * radius_nm + np.asarray(centre)
    truth = {'centre': np.asarray(centre, dtype=float), 'radius_nm': radius_nm}
    return points, truth

# ====================
# generate_spherical_cap_points: returns tuple of ndarray of points uniformly sampled on a spherical cap and dictionary of true parameters
# ====================
def generate_spherical_cap_points(
    radius_nm: float,
    half_angle_deg: float,
    centre: tuple[float, float, float] = (0.0, 0.0, 0.0),
    pole: tuple[float, float, float] | None = None,
    n: int = 500,
    seed: int | None = None,
) -> tuple[np.ndarray, dict]:
    '''
    Uniformly sample n points on a spherical cap (colatitude <= half_angle_deg from pole), simulating a segmentation that only captured one contiguous partial region of a sphere
    '''
    if half_angle_deg >= 180.0:
        points, truth = generate_full_sphere_points(radius_nm, centre, n, seed)
        truth.update({'half_angle_deg': half_angle_deg, 'pole': pole})
        return points, truth
    rng = np.random.default_rng(seed)
    pole = np.array(pole, dtype=float) if pole is not None else np.array([0.0, 0.0, 1.0])
    cos_min = np.cos(np.radians(half_angle_deg))
    cos_theta = rng.uniform(cos_min, 1.0, n)
    sin_theta = np.sqrt(1 - cos_theta ** 2)
    phi = rng.uniform(0, 2 * np.pi, n)
    local = np.stack([sin_theta * np.cos(phi), sin_theta * np.sin(phi), cos_theta], axis=1)
    points = _rotate_to_pole(local, pole) * radius_nm + np.asarray(centre)
    truth = {'centre': np.asarray(centre, dtype=float), 'radius_nm': radius_nm, 'half_angle_deg': half_angle_deg, 'pole': pole}
    return points, truth

# ====================
# generate_equatorial_band_points: returns tuple of ndarray of points uniformly sampled on an equatorial band and dictionary of true parameters
# ====================
def generate_equatorial_band_points(
    radius_nm: float,
    band_half_width_deg: float,
    centre: tuple[float, float, float] = (0.0, 0.0, 0.0),
    pole: tuple[float, float, float] | None = None,
    n: int = 500,
    seed: int | None = None,
) -> tuple[np.ndarray, dict]:
    '''
    Uniformly sample n points on a belt around the equator (colatitude within band_half_width_deg of 90 deg from pole), simulating the real-world missing-wedge geometry where data loss is concentrated near the poles relative to the tilt axis rather than a single contiguous chunk
    '''
    if band_half_width_deg >= 90.0:
        points, truth = generate_full_sphere_points(radius_nm, centre, n, seed)
        truth.update({'band_half_width_deg': band_half_width_deg, 'pole': pole})
        return points, truth
    rng = np.random.default_rng(seed)
    pole = np.array(pole, dtype=float) if pole is not None else np.array([0.0, 0.0, 1.0])
    cos_max = np.sin(np.radians(band_half_width_deg))
    cos_theta = rng.uniform(-cos_max, cos_max, n)
    sin_theta = np.sqrt(1 - cos_theta ** 2)
    phi = rng.uniform(0, 2 * np.pi, n)
    local = np.stack([sin_theta * np.cos(phi), sin_theta * np.sin(phi), cos_theta], axis=1)
    points = _rotate_to_pole(local, pole) * radius_nm + np.asarray(centre)
    truth = {'centre': np.asarray(centre, dtype=float), 'radius_nm': radius_nm, 'band_half_width_deg': band_half_width_deg, 'pole': pole}
    return points, truth
