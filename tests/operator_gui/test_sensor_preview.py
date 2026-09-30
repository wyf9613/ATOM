"""Use system Python with OpenCV/numpy, or run in the Jazzy container."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
try:
    import numpy as np
    import cv2
except ImportError:
    raise unittest.SkipTest('OpenCV/numpy tests run in the Jazzy container')
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/operator_gui'))
from sensor_preview import depth_preview,tag_preview

class SensorTests(unittest.TestCase):
    def message(self,data,encoding='32FC1',endian=b'\x00'):
        return NS(encoding=encoding,is_bigendian=endian,width=data.shape[1],height=data.shape[0],
                  step=data.shape[1]*data.dtype.itemsize,data=data.tobytes(),
                  header=NS(frame_id='camera',stamp=NS(sec=12,nanosec=0)))
    def test_float_depth_invalid_mask_and_png(self):
        values=np.array([[float('nan'),0,.25],[1.5,float('inf'),3]],dtype='<f4')
        png,m=depth_preview(self.message(values))
        self.assertEqual(m['valid_pixels'],2);self.assertAlmostEqual(m['valid_fraction'],2/6)
        self.assertAlmostEqual(m['median_m'],.875,places=6)
        decoded=cv2.imdecode(np.frombuffer(png,dtype=np.uint8),cv2.IMREAD_COLOR)
        self.assertEqual(decoded.shape,(2,3,3));self.assertTrue((decoded[0,0]==0).all())
    def test_big_endian_uint16_millimeters(self):
        _,m=depth_preview(self.message(np.array([[250,1500]],dtype='>u2'),'16UC1',b'\x01'))
        self.assertAlmostEqual(m['min_m'],.25);self.assertAlmostEqual(m['median_m'],.875,places=6)
    def test_known_apriltag_and_empty_image(self):
        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
        marker=cv2.aruco.drawMarker(dictionary,1,120)
        image=np.full((300,300,3),255,dtype=np.uint8);image[90:210,90:210]=cv2.cvtColor(marker,cv2.COLOR_GRAY2BGR)
        result=tag_preview(image.copy(),None,'camera')
        self.assertEqual(result['detected_ids'],[1]);self.assertFalse(result['pose_valid'])
        info=NS(header=NS(frame_id='camera'),k=[300.,0.,150.,0.,300.,150.,0.,0.,1.],d=[0.]*5)
        positioned=tag_preview(image,info,'camera')
        self.assertTrue(positioned['pose_valid'])
        self.assertAlmostEqual(positioned['poses_camera_m']['1'][2],.1,delta=.01)
        self.assertEqual(tag_preview(np.full((300,300,3),255,dtype=np.uint8))['detected_ids'],[])
if __name__=='__main__':unittest.main()
