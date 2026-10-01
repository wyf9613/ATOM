"""Coarse rack input contract; run inside the ROS container."""
import math
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
try:
    from geometry_msgs.msg import PoseStamped
except ImportError:
    raise unittest.SkipTest('Input contract tests require the sourced ROS container environment')
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ros2_ws/src/atom_xarm_sim'))
from atom_xarm_sim.pre_observation_target_pose import target_pose_from_command
from atom_xarm_sim.simulation.inputs import SimulationInputs

class InputTests(unittest.TestCase):
    def test_xy_controls_direction_height_preserved(self):
        command=PoseStamped();command.header.frame_id='link_base'
        command.pose.position.x=.6;command.pose.position.y=.8;command.pose.position.z=.247
        command.pose.orientation.w=1.0
        target,bearing=target_pose_from_command(command)
        self.assertAlmostEqual(bearing,math.atan2(.8,.6))
        self.assertAlmostEqual(target.pose.position.x,.21)
        self.assertAlmostEqual(target.pose.position.y,.28)
        self.assertEqual(target.pose.position.z,.247)
        command.pose.orientation.z=1.;command.pose.orientation.w=0.
        changed,_=target_pose_from_command(command)
        self.assertEqual(changed.pose.position,target.pose.position)
        self.assertEqual(changed.pose.orientation,target.pose.orientation)

    def test_invalid_xy_rejected(self):
        for x,y in [(0.,0.),(math.nan,1.),(1.,math.inf)]:
            command=PoseStamped();command.header.frame_id='link_base'
            command.pose.position.x=x;command.pose.position.y=y
            with self.assertRaises(ValueError):target_pose_from_command(command)

    def test_noisy_xy_published_but_height_exact(self):
        class Fixture(SimulationInputs):
            robot_frame='link_base'
            input_topic='/atom/pre_observation_target'
            def get_parameter(self,name):return SimpleNamespace(value={'xy_noise_m':.025,'random_seed':42}[name])
            def get_clock(self):return SimpleNamespace(now=lambda:SimpleNamespace(to_msg=lambda:PoseStamped().header.stamp))
            def get_logger(self):return SimpleNamespace(info=lambda _:None)
        node=Fixture();sent=[];node.input_publisher=SimpleNamespace(publish=sent.append)
        expected={}
        for tag,y in enumerate([.6,.67,.74,.81]):
            pose=PoseStamped();pose.pose.position.x=.5;pose.pose.position.y=y;pose.pose.position.z=.167
            expected[tag]=pose
        node._publish_provisional_input(expected)
        msg=sent[0]
        self.assertLessEqual(abs(msg.pose.position.x-.5),.025)
        self.assertLessEqual(abs(msg.pose.position.y-.705),.025)
        self.assertNotEqual((msg.pose.position.x,msg.pose.position.y),(.5,.705))
        self.assertAlmostEqual(msg.pose.position.z,.247)
        self.assertAlmostEqual(node.observation_bearing,math.atan2(msg.pose.position.y,msg.pose.position.x))
        node._publish_provisional_input(expected)
        self.assertEqual(sent[1],msg)
