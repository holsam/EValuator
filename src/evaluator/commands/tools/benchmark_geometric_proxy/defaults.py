'''
=======================================
EValuator: GEOMETRIC PROXY BENCHMARKING SCRIPT DEFAULTS
=======================================
'''

MIN_CAP_ANGLE = 15
MAX_CAP_ANGLE = 90
CAP_ANGLE_STEP = 15

MIN_BAND_WIDTH = 15
MAX_BAND_WIDTH = 90
BAND_WIDTH_STEP = 15

REPLICATES = 20
RADIUS = 10.0
N_POINTS = 500
SEED = 0

METHODS = {
    'naive bounding box': ('old_radius_nm', 'old_time_s'),
    'isotropy-aware bounding box': ('new_radius_nm', 'new_time_s'),
}
