'''
=======================================
EValuator: SYNTHETIC EV UTILITY FUNCTIONS
=======================================
Functions for generating synthetic EVs
'''

# Import external dependencies
import numpy as np

# generate_ev_shell: returns boolean array (Z,Y,X) and dictionary of true parameters
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

# apply_polar_gaps: returns boolean array derived from input shell with polar voxels removed
# -- nb fast geometric proxy for missing-wedge polar caps, is deterministic for unit testing
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

# apply_fourier_missing_wedge: returns boolean array with Fourier-space degradation to mimic missing wedge (tilt_range_deg = tilt-series half-range (i.e ±60° tilt series has half-range 60°); threshold = re-binarisation threshold for inverse-FFT magnitude relative to maximum)
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