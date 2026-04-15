'''
Sphere parameters (chosen to be representative of real EV scale at the synthetic dataset's voxel size):
    volume shape: (80, 80, 80) vox
    centre: (40, 40, 40)
    r_outer: 20 vox
    r_inner: 12 vox (shell thickness 8 vox, ~4.3 nm at 0.536 nm/vox)
    voxel size: 0.536 nm/vox (matching the synthetic dataset)
'''

# -- Import external dependencies ------
import pytest
import numpy as np
from scipy import ndimage
from skimage import measure

# -- Define sphere geometry constants --
VOX_NM_SMALL = 0.536
SMALL_VOL_SHAPE = (80, 80, 80)
CENTRE = (40, 40, 40)
R_OUTER = 20
R_INNER = 12

# -- Define module fixtures ------------
@pytest.fixture(scope="module")
def hollow_sphere_vol():
    """
    A (80, 80, 80) binary boolean volume containing a single hollow spherical
    shell: centre (40,40,40), r_outer=20, r_inner=12.

    Analytic shell voxel count (continuous): (4/3)π(20^3−12^3) ≈ 26,266 vox.
    Lumen voxel count (continuous): (4/3)π x 12^3 ≈ 7,238 vox.
    """
    vol = np.zeros(SMALL_VOL_SHAPE, dtype=bool)
    zz, yy, xx = np.indices(SMALL_VOL_SHAPE)
    cz, cy, cx = CENTRE
    dist = np.sqrt((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2)
    vol[(dist >= R_INNER) & (dist <= R_OUTER)] = True
    return vol

@pytest.fixture(scope="module")
def labelled_sphere_vol(hollow_sphere_vol):
    """
    Integer-labelled version of hollow_sphere_vol (background=0, sphere=1).
    Uses the same 6-connectivity as evaluator.utils.mrc.labelComponents.
    """
    struc = ndimage.generate_binary_structure(3, 1)
    labelled, _ = ndimage.label(hollow_sphere_vol.astype(np.int32), structure=struc)
    return labelled

@pytest.fixture(scope="module")
def sphere_regionprops(labelled_sphere_vol):
    """
    scikit-image RegionProperties object for the single hollow sphere
    component. Used to test functions that accept a regionprops object.
    """
    props = measure.regionprops(labelled_sphere_vol)
    assert len(props) == 1, "Expected exactly one component in labelled_sphere_vol"
    return props[0]