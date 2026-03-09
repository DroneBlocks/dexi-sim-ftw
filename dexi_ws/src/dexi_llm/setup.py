from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'dexi_llm'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(),
    package_data={package_name: ['config/*.json', 'config/*.txt']},
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Dennis Baldwin',
    maintainer_email='db@droneblocks.io',
    description='Local LLM inference for DEXI drone natural language commands',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'llm_node = dexi_llm.llm_node:main',
        ],
    },
)
