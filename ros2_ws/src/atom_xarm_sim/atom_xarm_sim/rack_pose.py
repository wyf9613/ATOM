"""Rigid, same-image two-tag pose for the provisional simulation rack."""
import cv2
import numpy as np


def estimate_rack_pair(corners_by_id, camera_matrix, distortion, tag_size, slot_y):
    half = tag_size / 2
    local = np.array([[-half, half, 0], [half, half, 0],
                      [half, -half, 0], [-half, -half, 0]], dtype=np.float64)
    centres = {tag: np.array([-(slot_y[tag]-slot_y[1]), 0, 0]) for tag in (1, 2)}
    objects = np.concatenate([local+centres[tag] for tag in (1, 2)])
    pixels = np.concatenate([corners_by_id[tag].reshape(4, 2) for tag in (1, 2)]).astype(np.float64)
    ok, rotation, translation = cv2.solvePnP(objects, pixels, camera_matrix, distortion)
    if not ok or translation[2, 0] <= 0:
        raise ValueError('two-tag board pose could not be estimated')
    projected, _ = cv2.projectPoints(objects, rotation, translation, camera_matrix, distortion)
    error = float(np.sqrt(np.mean(np.sum((projected.reshape(-1, 2)-pixels)**2, axis=1))))
    if error > 2.0:
        raise ValueError(f'two-tag board reprojection error {error:.3f} px exceeds 2 px')
    matrix, _ = cv2.Rodrigues(rotation)
    return {tag: (rotation, matrix @ centres[tag]+translation.reshape(3)) for tag in (1, 2)}
