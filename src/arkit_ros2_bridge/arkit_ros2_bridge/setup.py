from setuptools import setup
import os
from glob import glob

package_name = 'arkit_ros2_bridge'

setup(
    name=package_name,
    version='2.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Ayan Syed',
    maintainer_email='ayansyedca@gmail.com',
    description='UDP bridge for streaming iOS ARKit depth, rbg, and telemetry data',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # Maps the command 'udp_receiver' to the main() function in udp_receiver.py
            'iphoneInput = arkit_ros2_bridge.iphoneInput:main'
        ],
    },
)