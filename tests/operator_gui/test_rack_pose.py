"""Geometric regression: recover a rigid rack from known synthetic images."""
import sys
import unittest
from pathlib import Path
try:
    import numpy as np
    import cv2
except ImportError:
    raise unittest.SkipTest('OpenCV/numpy tests run in the Jazzy container')
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ros2_ws/src/atom_xarm_sim'))
from atom_xarm_sim.rack_pose import estimate_rack_pair, rack_observation_complete


class RackPoseTests(unittest.TestCase):
    def scene(self):
        k=np.array([[550.,0,320],[0,550.,240],[0,0,1]])
        rotation=np.array([3.05,.1,.2]);position=np.array([.01,.0,.55])
        matrix,_=cv2.Rodrigues(rotation)
        corners={}
        for tag,x in ((1,0.),(2,-.07)):
            points=np.array([[x-.02,.02,0],[x+.02,.02,0],
                             [x+.02,-.02,0],[x-.02,-.02,0]])
            projected,_=cv2.projectPoints(points,rotation,position,k,None)
            corners[tag]=projected.reshape(4,2)
        return corners,k,matrix,position

    def test_same_frame_pair_recovers_centres_and_tangent(self):
        corners,k,matrix,position=self.scene()
        poses=estimate_rack_pair(corners,k,None,.04,[-.105,-.035,.035,.105])
        np.testing.assert_allclose(poses[1][1],position,atol=1e-6)
        np.testing.assert_allclose(poses[2][1]-poses[1][1],matrix@np.array([-.07,0,0]),atol=1e-6)

    def test_pixel_noise_preserves_rigid_spacing(self):
        corners,k,_,position=self.scene()
        rng=np.random.default_rng(73)
        corners={tag:value+rng.normal(0,.2,value.shape) for tag,value in corners.items()}
        poses=estimate_rack_pair(corners,k,None,.04,[-.105,-.035,.035,.105])
        self.assertAlmostEqual(np.linalg.norm(poses[2][1]-poses[1][1]),.07,places=6)
        self.assertLess(np.linalg.norm(poses[1][1]-position),.01)

    def test_inconsistent_marker_corners_rejected(self):
        corners,k,_,_=self.scene()
        corners[2][0]+=[25,35]
        with self.assertRaises(ValueError):
            estimate_rack_pair(corners,k,None,.04,[-.105,-.035,.035,.105])

    def test_four_tag_board_includes_edge_targets(self):
        k=np.array([[550.,0,320],[0,550.,240],[0,0,1]])
        rotation=np.array([3.05,.1,.2]);position=np.array([.01,0.,.55])
        corners={}
        for tag in range(4):
            x=-tag*.07
            points=np.array([[x-.02,.02,0],[x+.02,.02,0],[x+.02,-.02,0],[x-.02,-.02,0]])
            corners[tag]=cv2.projectPoints(points,rotation,position,k,None)[0].reshape(4,2)
        poses=estimate_rack_pair(corners,k,None,.04,[-.105,-.035,.035,.105])
        self.assertEqual(set(poses),{0,1,2,3})
        matrix=cv2.Rodrigues(rotation)[0]
        np.testing.assert_allclose(poses[3][1],position+matrix@np.array([-.21,0,0]),atol=1e-6)
        self.assertTrue(rack_observation_complete(poses,[0,1,2,3],3))

    def test_missing_target_or_other_rack_rejected(self):
        self.assertFalse(rack_observation_complete({0:None,1:None,2:None},[0,1,2,3],3))
        self.assertFalse(rack_observation_complete({0:None,1:None,2:None,3:None},[0,1,2,3],7))
        self.assertFalse(rack_observation_complete({1:None,2:None,3:None},[0,1,2,3],1))
