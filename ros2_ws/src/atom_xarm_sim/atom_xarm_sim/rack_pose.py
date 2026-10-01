"""Rigid, same-image multi-tag pose for the provisional simulation rack."""
import cv2
import numpy as np


def estimate_rack_pair(corners_by_id, camera_matrix, distortion, tag_size, slot_y):
    tags = sorted(corners_by_id)
    if len(tags) < 2 or any(tag < 0 or tag >= len(slot_y) for tag in tags):
        raise ValueError('rack fit requires at least two known tag IDs')
    half = tag_size / 2
    local = np.array([[-half, half, 0], [half, half, 0],
                      [half, -half, 0], [-half, -half, 0]], dtype=np.float64)
    centres = {tag: np.array([-(slot_y[tag]-slot_y[tags[0]]), 0, 0]) for tag in tags}
    objects = np.concatenate([local+centres[tag] for tag in tags])
    pixels = np.concatenate([corners_by_id[tag].reshape(4, 2) for tag in tags]).astype(np.float64)
    ok, rotation, translation = cv2.solvePnP(objects, pixels, camera_matrix, distortion)
    if not ok or translation[2, 0] <= 0:
        raise ValueError('two-tag board pose could not be estimated')
    projected, _ = cv2.projectPoints(objects, rotation, translation, camera_matrix, distortion)
    error = float(np.sqrt(np.mean(np.sum((projected.reshape(-1, 2)-pixels)**2, axis=1))))
    if error > 2.0:
        raise ValueError(f'two-tag board reprojection error {error:.3f} px exceeds 2 px')
    matrix, _ = cv2.Rodrigues(rotation)
    return {tag: (rotation, matrix @ centres[tag]+translation.reshape(3)) for tag in tags}


def rack_observation_complete(poses, rack_tag_ids, target_tag_id):
    """Only a coherent frame containing this entire rack and its target completes observation."""
    return target_tag_id in rack_tag_ids and set(rack_tag_ids).issubset(poses)
