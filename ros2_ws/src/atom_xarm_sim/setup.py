from glob import glob
from setuptools import find_packages, setup


package_name = 'atom_xarm_sim'


setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Project ATOM',
    maintainer_email='project-atom@unimelb.edu.au',
    description='Headless simulation and smoke checks for the xArm 850 baseline.',
    license='BSD-3-Clause',
    entry_points={
        'console_scripts': [
            'trajectory_demo = atom_xarm_sim.trajectory_demo:main',
            'smoke_test = atom_xarm_sim.smoke_test:main',
            'target_publisher = atom_xarm_sim.target_publisher:main',
            'transfer_demo = atom_xarm_sim.transfer_demo:main',
        ],
    },
)
