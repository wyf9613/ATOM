"""Known-transform and degenerate-input tests for offline calibration."""
from pathlib import Path
import sys
import cv2
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/camera'))
from calibrate_hand_eye import solve


def matrix(rvec, position):
    result = np.eye(4)
    result[:3, :3] = cv2.Rodrigues(np.asarray(rvec, float))[0]
    result[:3, 3] = position
    return result


def dataset(degenerate=False):
    camera = matrix([.2, -.1, .3], [.02, -.07, .14])
    target = matrix([.1, .3, -.2], [.5, .2, .3])
    rng = np.random.default_rng(42)
    samples = []
    for _ in range(12):
        arm = matrix([0, 0, 0] if degenerate else rng.normal(0, .6, 3), rng.uniform(-.3, .3, 3))
        observed = np.linalg.inv(camera) @ np.linalg.inv(arm) @ target
        samples.append({'base_from_eef': arm.tolist(), 'camera_from_target': observed.tolist()})
    return {'samples': samples, 'holdout_indices': [10, 11]}, camera


def test_recovers_known_eye_in_hand_transform_and_heldout_poses():
    data, expected = dataset()
    result = solve(data)
    assert np.allclose(result['eef_from_camera'], expected, atol=1e-8)
    assert max(x['translation_residual_m'] for x in result['heldout_residuals_against_first_training_target']) < 1e-8
    assert not result['hardware_accepted']


def test_rejects_no_rotational_diversity():
    data, _ = dataset(True)
    with pytest.raises(ValueError, match='rotational diversity'):
        solve(data)
