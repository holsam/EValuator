'''
=======================================
EValuator: LABEL COMPONENT MERGE UTILITIES
=======================================
'''

# ====================
# Import external dependencies
# ====================
import numpy

# ====================
# Import EValuator label utilities
# ====================
from evaluator.commands.label.utils.geometric_proxies import estimateCentroidRadius

# =========================
# DEFINE FUNCTION: findMergeGroups
# =========================
def findMergeGroups(
    component_points: dict[int, numpy.ndarray],
    centre_tol_factor: float,
    radius_tol_pct: float,
) -> list[list[int]]:
    '''
    Returns groups of label_ids that should be merged, based on centroid proximity and radius-estimate consistency using union-find
    '''
    label_ids = list(component_points)
    proxies = {label_id: estimateCentroidRadius(pts) for label_id, pts in component_points.items()}
    parent = {label_id: label_id for label_id in label_ids}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i, id_a in enumerate(label_ids):
        centroid_a, radius_a = proxies[id_a]
        for id_b in label_ids[i + 1:]:
            centroid_b, radius_b = proxies[id_b]
            if _shouldMerge(centroid_a, radius_a, centroid_b, radius_b, centre_tol_factor, radius_tol_pct):
                union(id_a, id_b)

    groups: dict[int, list[int]] = {}
    for label_id in label_ids:
        groups.setdefault(find(label_id), []).append(label_id)
    return list(groups.values())

# =========================
# DEFINE FUNCTION: _shouldMerge
# =========================
def _shouldMerge(centroid_a, radius_a, centroid_b, radius_b, centre_tol_factor, radius_tol_pct) -> bool:
    '''Mutually-consistent check: centroid proximity and radius agreement.'''
    centre_distance = float(numpy.linalg.norm(centroid_a - centroid_b))
    centre_ok = centre_distance <= centre_tol_factor * (radius_a + radius_b)
    if max(radius_a, radius_b) == 0:
        radius_ok = False
    else:
        radius_ok = abs(radius_a - radius_b) / max(radius_a, radius_b) <= radius_tol_pct
    return centre_ok and radius_ok

# =========================
# DEFINE FUNCTION: applyMerges
# =========================
def applyMerges(labelled_volume: numpy.ndarray, merge_groups: list[list[int]]) -> numpy.ndarray:
    '''
    Relabel labelled_volume (on a copy) so every label_id in each merge group is replaced with the group's minimum label_id
    '''
    merged = labelled_volume.copy()
    for group in merge_groups:
        if len(group) <= 1:
            continue
        target = min(group)
        for label_id in group:
            if label_id != target:
                merged[merged == label_id] = target
    return merged
