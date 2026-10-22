from glob import glob
from pathlib import Path
from setuptools import find_packages, setup

setup(
    name='atom_base', version='0.1.0', packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/atom_base']),
        ('share/atom_base', ['package.xml', 'HANDOVER_SOURCES.json', 'NOTICE.md']),
        *[(f'share/atom_base/{d}', [p for p in glob(f'{d}/*') if Path(p).is_file()])
          for d in ('launch', 'config', 'maps', 'web')],
    ],
    install_requires=['setuptools'],
    entry_points={'console_scripts': [
        f'{name} = atom_base.{name}:main' for name in (
            'mission_manager', 'task_bridge', 'kinematic_fixture', 'velocity_gate',
            'fine_adjust_server', 'tag_goal_publisher', 'send_goal', 'imu_brick_node',
        )
    ]},
    tests_require=['pytest'],
)
