"""Synthetic registered RGB-D tests against known geometry, including bad depth."""
import sys,unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ros2_ws/src/atom_xarm_sim'))
from atom_xarm_sim.rack_pose import estimate_rack_pair
from atom_xarm_sim.perception.depth_fusion import fuse_rack_depth

class DepthTests(unittest.TestCase):
    def scene(self):
        k=np.array([[550.,0,320],[0,550.,240],[0,0,1.]])
        rotation=np.array([3.05,.1,.2]);translation=np.array([.10,0,.55])
        matrix=cv2.Rodrigues(rotation)[0];n=matrix[:,2];slots=[-.105,-.035,.035,.105]
        corners={}
        for tag in range(4):
            x=-tag*.07
            points=np.array([[x-.02,.02,0],[x+.02,.02,0],[x+.02,-.02,0],[x-.02,-.02,0]])
            corners[tag]=cv2.projectPoints(points,rotation,translation,k,None)[0].reshape(4,2)
        y,x=np.indices((480,640));rays=np.stack(((x-320)/550,(y-240)/550,np.ones_like(x)),axis=-1)
        depth=(n@translation)/(rays@n)
        return k,rotation,translation,corners,depth,slots

    def test_depth_improves_biased_rgb_distance(self):
        k,r,t,c,d,slots=self.scene()
        rng=np.random.default_rng(12)
        # Slightly shrunk corners simulate systematic image-scale error.
        pixels=np.concatenate(list(c.values()));centre=pixels.mean(axis=0)
        noisy={tag:centre+(v-centre)*.988+rng.normal(0,.12,v.shape) for tag,v in c.items()}
        rgb=estimate_rack_pair(noisy,k,None,.04,slots)
        fused,q=fuse_rack_depth(rgb,noisy,d+rng.normal(0,.0007,d.shape),k,None,.04,slots)
        self.assertTrue(q['used'])
        n=cv2.Rodrigues(r)[0][:,2]
        self.assertLess(abs(n@(fused[0][1]-t)),abs(n@(rgb[0][1]-t)))
        self.assertLess(abs(n@(fused[0][1]-t)),.002)
        self.assertAlmostEqual(np.linalg.norm(fused[3][1]-fused[0][1]),.21,places=6)

    def test_holes_fall_back_with_reason(self):
        k,r,t,c,d,slots=self.scene();rgb=estimate_rack_pair(c,k,None,.04,slots)
        fused,q=fuse_rack_depth(rgb,c,np.full_like(d,np.nan),k,None,.04,slots)
        self.assertIs(fused,rgb);self.assertFalse(q['used'])
        self.assertEqual(q['reason'],'insufficient_depth_support')

    def test_depth_conflict_rejected(self):
        k,r,t,c,d,slots=self.scene();rgb=estimate_rack_pair(c,k,None,.04,slots)
        with self.assertRaisesRegex(ValueError,'conflict'):
            fuse_rack_depth(rgb,c,d+.08,k,None,.04,slots)

    def test_outliers_do_not_bias_plane(self):
        k,r,t,c,d,slots=self.scene();rgb=estimate_rack_pair(c,k,None,.04,slots)
        rng=np.random.default_rng(7);d=d.copy();d[rng.random(d.shape)<.12]+=.2
        fused,q=fuse_rack_depth(rgb,c,d,k,None,.04,slots)
        self.assertTrue(q['used']);self.assertLess(np.linalg.norm(fused[0][1]-t),.002)

    def test_plane_normal_corrects_rgb_tilt(self):
        k,r,t,c,d,slots=self.scene()
        biased=r+np.array([.035,.015,0.])
        matrix=cv2.Rodrigues(biased)[0]
        rgb={tag:(biased.copy(),t+matrix@np.array([-tag*.07,0,0])) for tag in range(4)}
        fused,q=fuse_rack_depth(rgb,c,d,k,None,.04,slots)
        self.assertTrue(q['used'])
        truth=cv2.Rodrigues(r)[0][:,2]
        before=np.linalg.norm(matrix[:,2]-truth)
        after=np.linalg.norm(cv2.Rodrigues(fused[0][0])[0][:,2]-truth)
        self.assertLess(after,before*.2)
