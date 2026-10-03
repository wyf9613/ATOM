from setuptools import setup

setup(
    name='atom_gripper_hardware', version='0.1.0',
    packages=['atom_gripper_hardware'],
    data_files=[('share/ament_index/resource_index/packages', ['resource/atom_gripper_hardware']),
                ('share/atom_gripper_hardware', ['package.xml']),
                ('share/atom_gripper_hardware/launch', ['launch/sensor.launch.py','launch/hardware.launch.py'])],
    install_requires=['setuptools'],
    entry_points={'console_scripts': [
        'sensor_bridge = atom_gripper_hardware.sensor_bridge:main',
        'hardware_bridge = atom_gripper_hardware.hardware_bridge:main']},
)
