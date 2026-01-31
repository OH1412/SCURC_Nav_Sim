from setuptools import setup
import os
from glob import glob

package_name = 'yolov8_ros2'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        
        # 1. 安装 launch 文件夹下的所有 .py 文件
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        
        # 2. 安装 config 文件夹下的所有 .yaml 文件
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        
        # 3. 安装 config 文件夹下的 .pt 权重文件 (让系统能找到 best.pt)
        (os.path.join('share', package_name, 'config'), glob('config/*.pt')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ldl',
    maintainer_email='3082128164@qq.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'yolov8_node = yolov8_ros2.yolov8_node:main',
            'kfs_weapon_3d_grasp_node = yolov8_ros2.kfs_weapon_3d_grasp_node:main',
        ],
    },
)