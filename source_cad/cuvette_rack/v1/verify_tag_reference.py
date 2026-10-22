"""Optional network check against AprilRobotics reference images; no image rewriting."""
from pathlib import Path
from urllib.request import urlopen
from concurrent.futures import ThreadPoolExecutor
import json, hashlib
import cv2
import numpy as np

OUT=Path(__file__).resolve().parent


def verify(i):
    url=f'https://raw.githubusercontent.com/AprilRobotics/apriltag-imgs/master/tag36h11/tag36_11_{i:05d}.png'
    with urlopen(url,timeout=30) as response:
        data=response.read()
    reference=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_GRAYSCALE)
    assert reference.shape==(10,10), (i,reference.shape)
    bits=np.rot90(cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),i,8),2)
    assert np.array_equal(reference[1:9,1:9],bits),i
    assert np.all(reference[0,:]==255) and np.all(reference[-1,:]==255)
    assert np.all(reference[:,0]==255) and np.all(reference[:,-1]==255)
    return {'id':i,'url':url,'sha256':hashlib.sha256(data).hexdigest(),
            'reference_size_px':[10,10],'matches_generated_8x8':True}


if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        result=list(pool.map(verify,range(11)))
    (OUT/'tag_reference_checks.json').write_text(json.dumps({'checked_date':'2026-10-21','results':result},indent=2))
    print('IDs 0..10 exactly match AprilRobotics reference black-border/data pixels and white perimeter.')
