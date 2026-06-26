'''
=======================================
EValuator: GEOMETRIC ANALYSIS UTILITIES
=======================================
'''
# ====================
# Import external dependencies
# ====================
import numpy

# =========================
# DEFINE FUNCTION: deriveAxes
# =========================
def deriveAxes(intertia_tensor, voxel_size_nm=None):
    '''
    Derive semi-axes (a ≥ b ≥ c) of the best-fit ellipsoid from inertia tensor eigenvalues. eigvalsh returns eigenvalues in ascending order (I_a ≤ I_b ≤ I_c).
    '''
    eigvals = numpy.linalg.eigvalsh(intertia_tensor)
    eigvals = numpy.clip(eigvals, 0, None)
    with numpy.errstate(divide="ignore", invalid="ignore"):
        inv_sqrt = numpy.where(eigvals > 0, 1.0 / numpy.sqrt(eigvals), 0.0)
    return inv_sqrt

# =========================
# DEFINE FUNCTION: measureAxes
# =========================
def measureAxes(component, equiv_diameter_nm):
    '''
    Measure major and minor axes by approximating the EV as an ellipsoid. Semi-axes are derived from inertia tensor eigenvalues and scaled to real-world size using the equivalent diameter.
    '''
    inv_sqrt_axes = deriveAxes(intertia_tensor=component.inertia_tensor)
    geomean_inv_sqrt = (inv_sqrt_axes[0] * inv_sqrt_axes[1] * inv_sqrt_axes[2]) ** (1 / 3)
    if geomean_inv_sqrt > 0:
        axis_scale = (equiv_diameter_nm / 2.0) / geomean_inv_sqrt
    principal_semiaxis_a, principal_semiaxis_b, principal_semiaxis_c = inv_sqrt_axes * axis_scale
    major_axis = 2 * principal_semiaxis_a
    minor_axis = 2 * principal_semiaxis_c
    return major_axis, minor_axis


# =========================
# DEFINE FUNCTION: shellVolume
# =========================
def shellVolume(diameter_nm, voxel_size_nm, thickness_vox):
    '''
    Calculate the expected voxel count of a hollow spherical shell, used for the voxel-count size filter.
    '''
    r_outer = diameter_nm / (2 * voxel_size_nm)
    r_inner = max(0, r_outer - thickness_vox)
    return (4 / 3) * numpy.pi * (r_outer ** 3 - r_inner ** 3)