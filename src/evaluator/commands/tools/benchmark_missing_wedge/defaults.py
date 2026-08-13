'''
=======================================
EValuator: MISSING WEDGE BENCHMARKING SCRIPT DEFAULTS
=======================================
'''

MIN_DIAMETER = 30
MAX_DIAMETER = 300
DIAMETER_STEP = 40
REPLICATES = 10
VOXEL_SIZE = 2.0
TILT_RANGE = 60.0
DIAMETER_JITTER = 6.0
SHAPE_JITTER = 0.1
SEED = 0

METHODS = {
    'baseline': ('baseline_d_nm', 'baseline_time_s'),
    'anisotropic closing': ('closed_d_nm', 'closed_time_s'),
    'sphere fit': ('fit_d_nm', 'fit_time_s'),
    'convex hull': ('hull_d_nm', 'hull_time_s'),
    'XY-projection diameter': ('xy_d_nm', 'xy_time_s'),
}