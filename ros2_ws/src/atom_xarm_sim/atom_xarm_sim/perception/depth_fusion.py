"""Registered optical-Z depth constrains a rigid RGB tag board; no ROS node."""
import cv2
import numpy as np


def fuse_rack_depth(poses, corners, depth, k, distortion, tag_size, slot_y):
    """Return coherent poses and diagnostics. Poor support falls back; conflict rejects.

    Input depth must already be registered to RGB, in metres of optical Z.
    All thresholds below are provisional simulation settings, not sensor accuracy.
    """
    tags = sorted(poses)
    diagnostics = {'used': False, 'method': 'rgb_pnp', 'reason': 'insufficient_depth_support'}
    if len(tags) < 2:
        return poses, diagnostics
    depth = np.asarray(depth)
    if depth.ndim != 2:
        raise ValueError('registered depth must be a 2D image')
    regions = []
    coverage = {}
    for tag in tags:
        mask = np.zeros(depth.shape, np.uint8)
        cv2.fillConvexPoly(mask, np.rint(corners[tag].reshape(4, 2)).astype(np.int32), 1)
        mask = cv2.erode(mask, np.ones((5, 5), np.uint8))
        y, x = np.nonzero(mask)
        z = depth[y, x]
        valid = np.isfinite(z) & (z > .08) & (z < 2.)
        coverage[str(tag)] = {'pixels': len(z), 'valid': int(valid.sum())}
        if len(z) >= 15 and valid.mean() >= .5:
            pixels = np.column_stack((x[valid], y[valid])).astype(np.float64)
            rays = cv2.undistortPoints(pixels.reshape(-1, 1, 2), k, distortion).reshape(-1, 2)
            regions.append(np.column_stack((rays * z[valid, None], z[valid])))
    diagnostics['coverage'] = coverage
    if len(regions) < 2 or sum(map(len, regions)) < 80:
        return poses, diagnostics
    points = np.concatenate(regions)
    rng = np.random.default_rng(73)
    if len(points) > 600:
        points = points[rng.choice(len(points), 600, replace=False)]
    # RANSAC followed by SVD rejects holes/background/mixed edge depths.
    best = np.zeros(len(points), dtype=bool)
    for _ in range(80):
        a, b, c = points[rng.choice(len(points), 3, replace=False)]
        normal = np.cross(b-a, c-a)
        norm = np.linalg.norm(normal)
        if norm < 1e-8:
            continue
        normal /= norm
        inliers = np.abs((points-a) @ normal) < .004
        if inliers.sum() > best.sum():
            best = inliers
    diagnostics['inlier_fraction'] = float(best.mean())
    if best.sum() < 80 or best.mean() < .75:
        diagnostics['reason'] = 'nonplanar_or_outlier_depth'
        return poses, diagnostics
    plane_points = points[best]
    centre = plane_points.mean(axis=0)
    _, singular, vt = np.linalg.svd(plane_points-centre, full_matrices=False)
    if singular[1] / np.sqrt(len(plane_points)) < .006:
        diagnostics['reason'] = 'degenerate_plane_support'
        return poses, diagnostics
    normal = vt[-1]
    supported_regions = sum(int((np.abs((region-centre)@normal) < .004).sum()) >= 15 for region in regions)
    diagnostics['plane_supported_tag_regions'] = supported_regions
    if supported_regions < 2:
        diagnostics['reason'] = 'single_tag_plane_support'
        return poses, diagnostics
    rotation, translation = poses[tags[0]]
    rotation = np.asarray(rotation).reshape(3)
    translation = np.asarray(translation).reshape(3)
    rgb_normal = cv2.Rodrigues(rotation)[0][:, 2]
    if normal @ rgb_normal < 0:
        normal = -normal
    distance_error = abs(normal @ (translation-centre))
    angle = float(np.arccos(np.clip(normal @ rgb_normal, -1., 1.)))
    rms = float(np.sqrt(np.mean(((plane_points-centre) @ normal)**2)))
    diagnostics.update(plane_rms_m=rms, rgb_plane_distance_difference_m=float(distance_error),
                       rgb_plane_normal_difference_rad=angle, sampled_points=len(points))
    if rms > .003:
        diagnostics['reason'] = 'noisy_depth_plane'
        return poses, diagnostics
    if distance_error > .03 or angle > np.deg2rad(20):
        raise ValueError('depth/PnP plane conflict exceeds 30 mm / 20 deg')
    half = tag_size / 2
    local = np.array([[-half,half,0],[half,half,0],[half,-half,0],[-half,-half,0]])
    centres = {tag: np.array([-(slot_y[tag]-slot_y[tags[0]]),0.,0.]) for tag in tags}
    objects = np.concatenate([local+centres[tag] for tag in tags])
    pixels = np.concatenate([corners[tag].reshape(4,2) for tag in tags])
    # Joint pose fit: image corners anchor in-plane position/rotation; sampled
    # point-to-board residuals anchor normal/distance. Normalize point count so
    # frame resolution cannot silently change the relative weight.
    def residual(state):
        matrix = cv2.Rodrigues(state[:3])[0]
        projected = cv2.projectPoints(objects,state[:3],state[3:],k,distortion)[0].reshape(-1,2)
        image = (projected-pixels).ravel() / .7
        plane = (plane_points-state[3:]) @ matrix[:,2] / .002
        plane = plane * np.sqrt(len(image)/len(plane_points))
        return np.concatenate((image,plane))
    state = np.concatenate((rotation,translation))
    damping = 1e-3
    for _ in range(15):
        values = residual(state)
        jacobian = np.column_stack([(residual(state+np.eye(6)[axis]*1e-6)-values)/1e-6 for axis in range(6)])
        step = np.linalg.solve(jacobian.T@jacobian + damping*np.eye(6), -jacobian.T@values)
        candidate = state+step
        if np.sum(residual(candidate)**2) < np.sum(values**2):
            state=candidate;damping=max(damping/3,1e-8)
            if np.linalg.norm(step) < 1e-8:
                break
        else:
            damping *= 10
    projected=cv2.projectPoints(objects,state[:3],state[3:],k,distortion)[0].reshape(-1,2)
    reprojection=float(np.sqrt(np.mean(np.sum((projected-pixels)**2,axis=1))))
    matrix=cv2.Rodrigues(state[:3])[0]
    final_plane_rms=float(np.sqrt(np.mean(((plane_points-state[3:])@matrix[:,2])**2)))
    if state[5] <= 0 or reprojection > 2. or final_plane_rms > .004:
        raise ValueError('fused rack pose violates reprojection/depth residual gate')
    diagnostics.update(used=True, method='rgbd_joint_plane', reason=None,
                       reprojection_rms_px=reprojection, fused_plane_rms_m=final_plane_rms,
                       translation_change_m=float(np.linalg.norm(state[3:]-translation)))
    return {tag: (state[:3].copy(), matrix@centres[tag]+state[3:]) for tag in tags}, diagnostics
