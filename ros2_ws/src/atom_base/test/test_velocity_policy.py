import math
from atom_base.velocity_policy import VelocityPolicy


def ready(require_scan=False):
    p=VelocityPolicy(require_scan=require_scan)
    p.reset();assert p.enable(True)
    return p


def test_startup_stop_and_reset_never_replay_motion():
    p=VelocityPolicy(require_scan=False)
    assert not p.enable(True)
    p.receive('nav',.1,.1,0.)
    p.reset()
    assert p.output(.1)==(0.,0.)
    assert p.enable(True)
    assert p.output(.1)==(0.,0.)


def test_source_change_disarms_and_clears_both_publishers():
    p=ready();p.receive('nav',.1,.1,0.);p.receive('fine',.05,-.1,0.)
    assert p.output(.1)==(.1,.1)
    p.select('fine');assert p.output(.1)==(0.,0.)
    p.enable(True);assert p.output(.1)==(0.,0.)
    p.receive('fine',.05,-.1,.2);assert p.output(.2)==(.05,-.1)


def test_dead_source_or_clock_reversal_produces_zero():
    p=ready();p.receive('nav',.1,.1,1.)
    assert p.output(1.31)==(0.,0.)
    assert p.output(.99)==(0.,0.)


def test_stop_blocks_new_commands_until_explicit_reset_and_enable():
    p=ready();p.receive('nav',.1,.1,0.);p.stop()
    p.receive('nav',.1,.1,.1);assert not p.enable(True)
    assert p.output(.1)==(0.,0.)
    p.reset();p.enable(True);assert p.output(.1)==(0.,0.)


def test_scan_missing_stale_or_blocked_prevents_output():
    p=ready(True);p.receive('nav',.1,.1,1.)
    assert p.output(1.)==(0.,0.)
    p.scan_seen=1.;p.obstacle=False;assert p.output(1.)==(.1,.1)
    p.receive('nav',.1,.1,1.6);assert p.output(1.6)==(0.,0.)
    p.scan_seen=1.6;p.obstacle=True;assert p.output(1.6)==(0.,0.)


def test_nonfinite_command_latches_stop_and_caps_finite_speed():
    p=ready();p.receive('nav',2.,-2.,0.);assert p.output(0.)==(.15,-.2)
    p.receive('nav',math.nan,0.,.1);assert p.stopped
    assert p.output(.1)==(0.,0.)
