"""Simulation-only wrist camera and two-level tube-transfer fixtures."""

from pathlib import Path
import math
import xml.etree.ElementTree as ET


CAMERA_MODES = ('none', 'rgb', 'depth')
TAG_FAMILY = 'DICT_APRILTAG_36h11'
TAG_IDS = (0, 1, 2, 3)
SLOT_Y_M = (-0.105, -0.035, 0.035, 0.105)
SOURCE_SLOT_INDEX = 1
DESTINATION_SLOT_INDEX = 2
TAG_SIZE_M = 0.040


def add_wrist_camera(robot_description: str, mode: str) -> str:
    """Attach one provisional forward-looking camera below the demo gripper."""
    if mode not in CAMERA_MODES:
        raise ValueError(f'camera mode must be one of {CAMERA_MODES}')
    if mode == 'none':
        return robot_description
    root = ET.fromstring(robot_description)
    if root.tag != 'robot' or root.find(
            ".//link[@name='xarm_gripper_base_link']") is None:
        raise ValueError(
            'camera mode requires the G1 demo gripper and '
            'xarm_gripper_base_link'
        )
    if root.find(".//link[@name='wrist_camera_link']") is not None:
        raise ValueError('wrist camera already exists')

    camera_link = ET.SubElement(root, 'link', name='wrist_camera_link')
    inertial = ET.SubElement(camera_link, 'inertial')
    ET.SubElement(inertial, 'mass', value='0.10')
    ET.SubElement(inertial, 'inertia', ixx='0.0001', ixy='0', ixz='0',
                  iyy='0.0001', iyz='0', izz='0.0001')
    visual = ET.SubElement(camera_link, 'visual')
    geometry = ET.SubElement(visual, 'geometry')
    ET.SubElement(geometry, 'box', size='0.045 0.035 0.025')
    collision = ET.SubElement(camera_link, 'collision')
    collision_geometry = ET.SubElement(collision, 'geometry')
    ET.SubElement(collision_geometry, 'box', size='0.045 0.035 0.025')
    material = ET.SubElement(visual, 'material', name='atom_camera_black')
    ET.SubElement(material, 'color', rgba='0.08 0.09 0.11 1')
    joint = ET.SubElement(root, 'joint', name='wrist_camera_mount', type='fixed')
    ET.SubElement(joint, 'parent', link='xarm_gripper_base_link')
    ET.SubElement(joint, 'child', link='wrist_camera_link')
    # The G1 points along gripper +Z while the Gazebo camera looks along its
    # local +X. Ry(-pi/2) aligns those axes. The provisional offset places the
    # camera below and forward of the gripper body without centring it between
    # the fingers; replace it with the measured bracket transform later.
    ET.SubElement(joint, 'origin', xyz='-0.080 0 0.060',
                  rpy='0 -1.57079632679 0')

    optical = ET.SubElement(root, 'link', name='wrist_camera_optical_frame')
    optical_joint = ET.SubElement(root, 'joint', name='wrist_camera_optical_joint', type='fixed')
    ET.SubElement(optical_joint, 'parent', link='wrist_camera_link')
    ET.SubElement(optical_joint, 'child', link='wrist_camera_optical_frame')
    ET.SubElement(optical_joint, 'origin', xyz='0 0 0',
                  rpy='-1.57079632679 0 -1.57079632679')

    gazebo = ET.SubElement(root, 'gazebo', reference='wrist_camera_link')
    sensor = ET.SubElement(gazebo, 'sensor', name='atom_wrist_camera',
                           type='camera' if mode == 'rgb' else 'rgbd_camera')
    ET.SubElement(sensor, 'always_on').text = 'true'
    ET.SubElement(sensor, 'update_rate').text = '10'
    ET.SubElement(sensor, 'topic').text = '/atom/wrist_camera'
    ET.SubElement(sensor, 'gz_frame_id').text = 'wrist_camera_optical_frame'
    camera = ET.SubElement(sensor, 'camera')
    ET.SubElement(camera, 'horizontal_fov').text = '1.0472'
    image = ET.SubElement(camera, 'image')
    ET.SubElement(image, 'width').text = '640'
    ET.SubElement(image, 'height').text = '480'
    clip = ET.SubElement(camera, 'clip')
    ET.SubElement(clip, 'near').text = '0.08'
    ET.SubElement(clip, 'far').text = '2.0'
    return ET.tostring(root, encoding='unicode')


def allow_wrist_camera_self_collisions(semantic_description: str,
                                       robot_description: str) -> str:
    """Allow the fixed sensor body to overlap the robot's own links in MoveIt.

    The camera is a rigid child of the gripper, so its collision geometry must
    not make every arm start state invalid. It remains available for future
    environment collision modelling; only robot-internal pairs are disabled.
    """
    semantic_root = ET.fromstring(semantic_description)
    robot_root = ET.fromstring(robot_description)
    link_names = [link.attrib['name'] for link in robot_root.findall('link')]
    existing = {
        frozenset((item.attrib.get('link1'), item.attrib.get('link2')))
        for item in semantic_root.findall('disable_collisions')
    }
    for link_name in link_names:
        if link_name == 'wrist_camera_link':
            continue
        pair = frozenset(('wrist_camera_link', link_name))
        if pair in existing:
            continue
        ET.SubElement(
            semantic_root,
            'disable_collisions',
            link1='wrist_camera_link',
            link2=link_name,
            reason='FixedSensor',
        )
    return ET.tostring(semantic_root, encoding='unicode')


def experiment_world(source_world: str, destination: Path) -> Path:
    """Add rendering systems to the pinned vendor table world."""
    tree = ET.parse(source_world)
    world = tree.getroot().find('world')
    if world is None:
        raise ValueError('vendor file has no SDF world')
    gravity = world.find('gravity')
    if gravity is None:
        gravity = ET.SubElement(world, 'gravity')
    gravity.text = '0 0 -9.81'
    systems = {
        'Physics': 'physics',
        'UserCommands': 'user-commands',
        'SceneBroadcaster': 'scene-broadcaster',
        'Sensors': 'sensors',
    }
    for name, filename_part in systems.items():
        plugin = ET.SubElement(world, 'plugin',
                               filename=f'gz-sim-{filename_part}-system',
                               name=f'gz::sim::systems::{name}')
        if name == 'Sensors':
            ET.SubElement(plugin, 'render_engine').text = 'ogre2'
    tree.write(destination, encoding='unicode', xml_declaration=True)
    return destination


def _box(parent, name, size, pose, color, collision=False):
    visual = ET.SubElement(parent, 'visual', name=name)
    ET.SubElement(visual, 'pose').text = pose
    geometry = ET.SubElement(visual, 'geometry')
    ET.SubElement(ET.SubElement(geometry, 'box'), 'size').text = size
    material = ET.SubElement(visual, 'material')
    ET.SubElement(material, 'ambient').text = color
    ET.SubElement(material, 'diffuse').text = color
    ET.SubElement(material, 'emissive').text = color
    if collision:
        coll = ET.SubElement(parent, 'collision', name=f'{name}_collision')
        ET.SubElement(coll, 'pose').text = pose
        geo = ET.SubElement(coll, 'geometry')
        ET.SubElement(ET.SubElement(geo, 'box'), 'size').text = size


def write_tag_rack(destination: Path) -> Path:
    """Generate the four-slot rack with one front-facing tag per slot."""
    import cv2
    dictionary = cv2.aruco.Dictionary_get(getattr(cv2.aruco, TAG_FAMILY))
    sdf = ET.Element('sdf', version='1.9')
    model = ET.SubElement(sdf, 'model', name='atom_source_rack')
    ET.SubElement(model, 'static').text = 'true'
    link = ET.SubElement(model, 'link', name='rack')
    _box(link, 'rack_body', '0.125 0.31 0.018', '0 0 0 0 0 0',
         '0.15 0.20 0.27 1', collision=True)
    _box(link, 'front_rail', '0.006 0.31 0.055', '-0.065 0 0.028 0 0 0',
         '0.15 0.20 0.27 1', collision=True)
    for x_label, x in (('left', 0.010), ('right', 0.050)):
        for y_label, y in (('front', -0.145), ('back', 0.145)):
            _box(link, f'guide_post_{x_label}_{y_label}', '0.006 0.006 0.046',
                 f'{x:.3f} {y:.3f} 0.027 0 0 0',
                 '0.22 0.28 0.34 1', collision=True)
    black = '0.005 0.005 0.005 1'
    white = '1 1 1 1'
    for slot, y in enumerate(SLOT_Y_M):
        # Four upper guide rails leave an open 20 mm square around the tube;
        # the lower rack body supports its sealed end.
        for side, yy in (('front', y - 0.012), ('back', y + 0.012)):
            _box(link, f'slot_{slot}_{side}', '0.028 0.004 0.008',
                 f'0.030 {yy:.6f} 0.048 0 0 0', '0.22 0.28 0.34 1',
                 collision=True)
        for side, x in (('left', 0.018), ('right', 0.042)):
            _box(link, f'slot_{slot}_{side}', '0.004 0.028 0.008',
                 f'{x:.6f} {y:.6f} 0.048 0 0 0', '0.22 0.28 0.34 1',
                 collision=True)
        # A bright white plate gives every marker a quiet zone.
        _box(link, f'tag_{slot}_plate', '0.001 0.048 0.048',
             f'-0.0685 {y:.6f} 0.029 0 0 0', white)
        _box(link, f'tag_{slot}_black_backing', f'0.0002 {TAG_SIZE_M:.6f} {TAG_SIZE_M:.6f}',
             f'-0.0692 {y:.6f} 0.029 0 0 0', black)
        marker_cells = dictionary.markerSize + 2  # one black border module
        marker = cv2.aruco.drawMarker(dictionary, TAG_IDS[slot], marker_cells)
        assert marker.shape == (marker_cells, marker_cells)
        cell = TAG_SIZE_M / marker_cells
        centre = (marker_cells - 1) / 2
        for row in range(marker_cells):
            for col in range(marker_cells):
                if marker[row, col] >= 128:
                    # Viewed from the outward -X normal, image-right is -Y.
                    # Reversing this axis avoids mirroring the AprilTag code.
                    yy = y - (col - centre) * cell
                    z = 0.029 + (centre - row) * cell
                    _box(link, f'tag_{slot}_{row}_{col}',
                         f'0.0002 {cell:.6f} {cell:.6f}',
                         f'-0.0695 {yy:.6f} {z:.6f} 0 0 0', white)
    ET.ElementTree(sdf).write(destination, encoding='unicode', xml_declaration=True)
    return destination


def write_two_level_shelf(destination: Path) -> Path:
    """A table-mounted second tier supporting the source rack."""
    sdf = ET.Element('sdf', version='1.9')
    model = ET.SubElement(sdf, 'model', name='atom_two_level_shelf')
    ET.SubElement(model, 'static').text = 'true'
    link = ET.SubElement(model, 'link', name='shelf')
    _box(link, 'upper_shelf', '0.17 0.43 0.018',
         '0 0 0.120 0 0 0', '0.64 0.66 0.68 1', collision=True)
    for x_label, x in (('front', -0.075), ('back', 0.075)):
        for y_label, y in (('left', -0.195), ('right', 0.195)):
            _box(link, f'post_{x_label}_{y_label}', '0.016 0.016 0.112',
                 f'{x:.3f} {y:.3f} 0.055 0 0 0',
                 '0.45 0.47 0.50 1', collision=True)
    ET.ElementTree(sdf).write(destination, encoding='unicode', xml_declaration=True)
    return destination


def write_transparent_tube(destination: Path) -> Path:
    """Dynamic hollow tube with translucent wall segments and a closed bottom."""
    sdf = ET.Element('sdf', version='1.9')
    model = ET.SubElement(sdf, 'model', name='atom_transfer_tube')
    ET.SubElement(model, 'static').text = 'false'
    ET.SubElement(model, 'allow_auto_disable').text = 'false'
    link = ET.SubElement(model, 'link', name='tube')
    inertial = ET.SubElement(link, 'inertial')
    ET.SubElement(inertial, 'mass').text = '0.015'
    inertia = ET.SubElement(inertial, 'inertia')
    for key, value in {'ixx': '0.000012', 'iyy': '0.000012', 'izz': '0.000001',
                       'ixy': '0', 'ixz': '0', 'iyz': '0'}.items():
        ET.SubElement(inertia, key).text = value
    def add_part(name, pose, shape, dimensions):
        for kind in ('visual', 'collision'):
            part = ET.SubElement(link, kind, name=f'{name}_{kind}')
            ET.SubElement(part, 'pose').text = pose
            geometry = ET.SubElement(part, 'geometry')
            primitive = ET.SubElement(geometry, shape)
            if shape == 'box':
                ET.SubElement(primitive, 'size').text = dimensions
            else:
                radius, length = dimensions
                ET.SubElement(primitive, 'radius').text = str(radius)
                ET.SubElement(primitive, 'length').text = str(length)
            if kind == 'visual':
                material = ET.SubElement(part, 'material')
                ET.SubElement(material, 'ambient').text = '0.72 0.91 0.96 0.28'
                ET.SubElement(material, 'diffuse').text = '0.72 0.91 0.96 0.28'
                ET.SubElement(part, 'transparency').text = '0.72'
            else:
                surface = ET.SubElement(part, 'surface')
                ode = ET.SubElement(ET.SubElement(surface, 'friction'), 'ode')
                ET.SubElement(ode, 'mu').text = '0.6'
                ET.SubElement(ode, 'mu2').text = '0.6'

    # Twelve facets approximate a 1 mm wall while leaving an open bore.
    for index in range(12):
        angle = 2.0 * math.pi * index / 12.0
        x = 0.00645 * math.cos(angle)
        y = 0.00645 * math.sin(angle)
        yaw = angle + math.pi / 2.0
        add_part(f'wall_{index}', f'{x:.7f} {y:.7f} 0.0015 0 0 {yaw:.7f}',
                 'box', '0.0034 0.0011 0.092')
    add_part('sealed_bottom', '0 0 -0.046 0 0 0', 'cylinder', (0.0068, 0.003))
    ET.ElementTree(sdf).write(destination, encoding='unicode', xml_declaration=True)
    return destination
