"""Pure control law for the fine adjust (no ROS), so it can be unit-tested and simulated.

Park, J.J. & Kuipers, B. (2011) "A smooth control law for graceful motion of differential wheeled
mobile robots in an intelligent environment", ICRA.  Egocentric polar coordinates of the target:
    r      distance to the target point
    los    bearing of the target point in the robot frame, atan2(y, x)
    delta  = -los            robot heading w.r.t. the line of sight
    theta  = yaw_t - los     target heading w.r.t. the line of sight
    kappa  = -(1/r) [ k2 (delta - atan(-k1 theta)) + (1 + k1 / (1 + (k1 theta)^2)) sin(delta) ]
    v      = v_max / (1 + beta |kappa|^lam),   w = kappa v
"""
import math


def wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


DEFAULTS = dict(v_max=0.05, v_min=0.012, w_max=0.25, w_min=0.04, k1=1.0, k2=3.0, beta=0.4, lam=2.0,
                slow_dist=0.25, k_turn=1.0, in_place_angle=math.radians(60.0), xy_tol=0.02,
                yaw_tol=math.radians(2.0), allow_reverse=False,
                final_dist=0.15, final_los=math.radians(8.0), k_lin=0.4)


def step(x, y, yaw_t, cfg, state):
    """One control step. (x, y, yaw_t) = target pose in the robot frame. state = {'phase': ...}.
    Returns (v, w, done, info)."""
    c = cfg
    r = math.hypot(x, y)
    los = math.atan2(y, x)

    if state['phase'] == 'final' and r > 2.5 * c['xy_tol']:
        state['phase'] = 'drive'
    if state['phase'] != 'final' and r <= c['xy_tol']:
        state['phase'] = 'final'

    if state['phase'] == 'final':
        if abs(yaw_t) <= c['yaw_tol']:
            return 0.0, 0.0, True, f'reached r={r*100:.1f} cm yaw={math.degrees(yaw_t):.1f} deg'
        w = c['k_turn'] * yaw_t
        w = math.copysign(max(abs(w), c['w_min']), w)
        return 0.0, max(-c['w_max'], min(c['w_max'], w)), False, f'final turn {math.degrees(yaw_t):+.1f} deg'

    # end game: inside final_dist the arc law would demand curvatures the base cannot follow (it circles the
    # goal at its minimum turning radius v_min/w_max), so: face the goal point, drive straight, then align yaw.
    if r <= c.get('final_dist', 0.0):
        if abs(los) > c['final_los']:
            w = c['k_turn'] * los
            w = math.copysign(max(abs(w), c['w_min']), w)
            return 0.0, max(-c['w_max'], min(c['w_max'], w)), False, f'end game: face goal point {math.degrees(los):+.1f} deg'
        v = max(c['v_min'], min(c['v_max'], c['k_lin'] * r))
        w = max(-c['w_max'], min(c['w_max'], c['k_turn'] * los))
        return v, w, False, f'end game: straight r={r*100:.1f} cm los={math.degrees(los):+.1f} deg'

    reverse = False
    if abs(los) > c['in_place_angle']:
        if c['allow_reverse'] and abs(los) > math.radians(120.0):
            reverse = True
        else:
            w = c['k_turn'] * los
            w = math.copysign(max(abs(w), c['w_min']), w)
            return 0.0, max(-c['w_max'], min(c['w_max'], w)), False, f'turn to face target {math.degrees(los):+.1f} deg'
    if reverse:   # mirror the problem: drive the back of the robot towards the target
        x, y, los, yaw_t = -x, -y, wrap(los + math.pi), wrap(yaw_t + math.pi)

    delta = -los
    theta = wrap(yaw_t - los)
    k1, k2 = c['k1'], c['k2']
    kappa = -(1.0 / max(r, 1e-3)) * (k2 * (delta - math.atan(-k1 * theta))
                                     + (1.0 + k1 / (1.0 + (k1 * theta) ** 2)) * math.sin(delta))
    v = c['v_max'] / (1.0 + c['beta'] * abs(kappa) ** c['lam'])
    v = min(v, c['v_max'] * r / c['slow_dist'])
    v = max(v, c['v_min'])
    w = kappa * v
    if abs(w) > c['w_max']:            # keep the curvature: slow down rather than clipping w alone
        s = c['w_max'] / abs(w)
        v, w = v * s, w * s
    if reverse:
        v = -v
    return v, w, False, f'arc r={r*100:.1f} cm los={math.degrees(los):+.1f} deg kappa={kappa:+.2f}'


def target_in_robot_frame(robot_xyyaw, goal_xyyaw):
    bx, by, byaw = robot_xyyaw
    gx, gy, gyaw = goal_xyyaw
    dx, dy = gx - bx, gy - by
    cs, sn = math.cos(-byaw), math.sin(-byaw)
    return cs * dx - sn * dy, sn * dx + cs * dy, wrap(gyaw - byaw)
