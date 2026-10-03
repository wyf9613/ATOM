"""Read-only image diagnostics; no detection result is used to command motion."""
import numpy as np
import cv2

MIN_DEPTH_M=.08
MAX_DEPTH_M=2.

def depth_preview(message):
    encodings={'32FC1':('f4',1.),'16UC1':('u2',.001)}
    if message.encoding not in encodings:raise ValueError('Unsupported depth encoding '+message.encoding)
    kind,scale=encodings[message.encoding]
    endian=int.from_bytes(message.is_bigendian,'little') if isinstance(message.is_bigendian,bytes) else int(message.is_bigendian)
    dtype=np.dtype(('>' if endian else '<')+kind)
    if not (0<message.height and 0<message.width and message.width*message.height<=4_000_000):raise ValueError('Invalid depth dimensions')
    if message.step%dtype.itemsize or message.step<message.width*dtype.itemsize:raise ValueError('Invalid depth row stride')
    image=np.frombuffer(bytes(message.data),dtype=dtype).reshape(message.height,message.step//dtype.itemsize)[:,:message.width].astype(np.float32)*scale
    valid=np.isfinite(image)&(image>MIN_DEPTH_M)&(image<MAX_DEPTH_M)
    clipped=np.nan_to_num(image,nan=MAX_DEPTH_M,posinf=MAX_DEPTH_M,neginf=MAX_DEPTH_M)
    scaled=(255*(1-(np.clip(clipped,MIN_DEPTH_M,MAX_DEPTH_M)-MIN_DEPTH_M)/(MAX_DEPTH_M-MIN_DEPTH_M))).astype(np.uint8)
    color=cv2.applyColorMap(scaled,cv2.COLORMAP_TURBO);color[~valid]=0
    ok,png=cv2.imencode('.png',color,[cv2.IMWRITE_PNG_COMPRESSION,1])
    if not ok:raise ValueError('Depth PNG encoding failed')
    metrics={'width':message.width,'height':message.height,'encoding':message.encoding,'unit':'m',
             'valid_fraction':float(valid.mean()),'valid_pixels':int(valid.sum()),
             'min_m':float(image[valid].min()) if valid.any() else None,
             'max_m':float(image[valid].max()) if valid.any() else None,
             'median_m':float(np.median(image[valid])) if valid.any() else None,
             'display_min_m':MIN_DEPTH_M,'display_max_m':MAX_DEPTH_M,
             'source_stamp_s':message.header.stamp.sec+message.header.stamp.nanosec*1e-9,
             'frame':message.header.frame_id}
    return png.tobytes(),metrics

def tag_preview(image, camera_info=None, frame=None):
    dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
    params=cv2.aruco.DetectorParameters_create() if hasattr(cv2.aruco,'DetectorParameters_create') else cv2.aruco.DetectorParameters()
    params.minMarkerDistanceRate=.01;params.minMarkerPerimeterRate=.02
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    if hasattr(cv2.aruco,'ArucoDetector'):
        # AprilTag contour refinement preserves the marker border in newer OpenCV
        # when the small inter-marker distance setting groups nested candidates.
        params.cornerRefinementMethod=cv2.aruco.CORNER_REFINE_APRILTAG
        corners,ids,_=cv2.aruco.ArucoDetector(dictionary,params).detectMarkers(gray)
    else:
        corners,ids,_=cv2.aruco.detectMarkers(gray,dictionary,parameters=params)
    detected=[] if ids is None else [int(i) for i in ids.flatten()]
    # Each slot has a unique ID. Nested contour candidates can decode twice.
    if detected:
        best={}
        for index,tag in enumerate(detected):
            if tag not in best or abs(cv2.contourArea(corners[index].reshape(-1,2))) > abs(cv2.contourArea(corners[best[tag]].reshape(-1,2))):
                best[tag]=index
        indices=list(best.values())
        corners=[corners[i] for i in indices]
        ids=np.asarray([detected[i] for i in indices],dtype=np.int32).reshape(-1,1)
        detected=[int(i) for i in ids.flatten()]
    poses={}
    if detected:
        cv2.aruco.drawDetectedMarkers(image,corners,ids)
        if camera_info and camera_info.header.frame_id==frame and camera_info.k[0]>0:
            k=np.asarray(camera_info.k,dtype=float).reshape(3,3)
            d=np.asarray(camera_info.d,dtype=float)
            if hasattr(cv2.aruco,'estimatePoseSingleMarkers'):
                _,tvecs,_=cv2.aruco.estimatePoseSingleMarkers(corners,.04,k,d)
                poses={str(i):[float(v) for v in t.reshape(3)] for i,t in zip(detected,tvecs)}
            else:
                square=np.array([[-.02,.02,0],[.02,.02,0],[.02,-.02,0],[-.02,-.02,0]],dtype=np.float32)
                for i,c in zip(detected,corners):
                    ok,_,t=cv2.solvePnP(square,c.reshape(4,2),k,d,flags=cv2.SOLVEPNP_IPPE_SQUARE)
                    if ok: poses[str(i)]=[float(v) for v in t.reshape(3)]
    return {'family':'AprilTag 36h11','detected_ids':detected,'detected':bool(detected),
            'poses_camera_m':poses,'pose_method':'RGB PnP','tag_size_m':.04,
            'frame':frame,'pose_valid':bool(poses)}
