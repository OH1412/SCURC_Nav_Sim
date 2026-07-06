from glob import glob
from setuptools import find_packages, setup

package_name = 'legged_mission_planner'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/config/scenarios', glob('config/scenarios/*.yaml')),
        ('share/' + package_name + '/assets', glob('assets/*')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools', 'Pillow'],
    zip_safe=True,
    maintainer='oh',
    maintainer_email='1294595013@qq.com',
    description='Decoupled mission path planner for the ROBOCON legged robot task event.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mission_ui = legged_mission_planner.ui_labeling:main',
            'export_scenarios = legged_mission_planner.path_enumerator:main',
        ],
    },
)
