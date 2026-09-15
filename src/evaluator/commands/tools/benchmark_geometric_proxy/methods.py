'''
=======================================
EValuator: GEOMETRIC PROXY BENCHMARKING SCRIPT METHODS
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy as np

# ====================
# Define method functions
# ====================
# -- bbox_centroid_radius: returns tuple of ndarray, float
def bbox_centroid_radius(points: np.ndarray) -> tuple[np.ndarray, float]:
    '''
    Estimate centre/radius as point mean / half the mean bounding-box extent (naive bounding-box)
    '''
    centroid = points.mean(axis=0)
    extent = points.max(axis=0) - points.min(axis=0)
    radius_estimate = float(np.mean(extent) / 2.0)
    return centroid, radius_estimate
