#!/usr/bin/env python

from distutils.core import setup
from catkin_pkg.python_setup import generate_distutils_setup

d = generate_distutils_setup(
    packages=['data_acquisition_2d'],
    package_dir={'': 'src'},
    scripts=['scripts/data_acquisition_2d']
)

setup(**d)
