"""Offline eye-in-hand solve from measured synchronized poses; no robot access.

JSON: samples[{base_from_eef:4x4,camera_from_target:4x4}], holdout_indices:[...].
Transforms use metres, column vectors and right-handed rotation matrices.
"""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np


def transform(value):
    matrix = np.asarray(value, dtype=float)
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError('Expected finite 4x4 transform')
    if not np.allclose(matrix[3], [0, 0, 0, 1], atol=1e-8):
        raise ValueError('Invalid homogeneous last row')
    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(rotation), 1, atol=1e-6):
        raise ValueError('Rotation must be right-handed orthonormal')
    return matrix


def solve(data):
    pairs = [(transform(s['base_from_eef']), transform(s['camera_from_target']))
             for s in data['samples']]
    holdout = set(data['holdout_indices'])
    if not holdout or any(type(i) is not int or i < 0 or i >= len(pairs) for i in holdout):
        raise ValueError('Require explicit valid held-out indices')
    train = [p for i, p in enumerate(pairs) if i not in holdout]
    if len(train) < 8:
        raise ValueError('Require at least 8 training poses plus held-out poses')
    relative_rotations = [cv2.Rodrigues(train[0][0][:3, :3].T @ a[:3, :3])[0].ravel()
                          for a, _ in train[1:]]
    singular = np.linalg.svd(np.asarray(relative_rotations), compute_uv=False)
    if singular[1] < 0.1:
        raise ValueError('Insufficient rotational diversity: need rotations about multiple axes')
    rotation, translation = cv2.calibrateHandEye(
        [a[:3, :3] for a, _ in train], [a[:3, 3] for a, _ in train],
        [b[:3, :3] for _, b in train], [b[:3, 3] for _, b in train],
        method=cv2.CALIB_HAND_EYE_PARK)
    result = np.eye(4)
    result[:3, :3], result[:3, 3] = rotation, translation.ravel()
    result = transform(result)
    targets = [a @ result @ b for a, b in train]
    reference = targets[0]
    residuals = []
    for index in sorted(holdout):
        a, b = pairs[index]
        measured = a @ result @ b
        angle = np.linalg.norm(cv2.Rodrigues(reference[:3, :3].T @ measured[:3, :3])[0])
        residuals.append({'index': index, 'translation_residual_m': float(np.linalg.norm(measured[:3, 3] - reference[:3, 3])),
                          'rotation_residual_rad': float(angle)})
    return {'eef_from_camera': result.tolist(), 'method': 'OpenCV PARK',
            'opencv_version': cv2.__version__, 'units': 'm/rad',
            'train_count': len(train), 'holdout_count': len(holdout),
            'rotation_diversity_singular_values_rad': singular.tolist(),
            'heldout_residuals_against_first_training_target': residuals,
            'hardware_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = solve(json.loads(args.input.read_text()))
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(args.output)


if __name__ == '__main__':
    main()
