#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2019-2021 by Murray Altheim. All rights reserved. This file is part
# of the K-Series Robot Operating System (KROS) project, released under the MIT
# License. Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-04-21
#
# See: https://setuptools.readthedocs.io/en/latest/userguide/index.html
#      https://setuptools.readthedocs.io/en/latest/userguide/quickstart.html
#
#   future requires:
#       'psutil',
#       'gpiozero',
#       'board',
#       'pyquaternion'
#       'rpi.gpio', \
#       'adafruit-extended-bus', \
#       'pymessagebus==1.*', \
#       'ht0740', \
#       'pimoroni-ioexpander', \
#       'adafruit-circuitpython-bno08x', \
#       'matrix11x7', \
#       'rgbmatrix5x5', \
#
# To build the package:
#
#  % python3 -m build
#
# To run tests:
#
#  % pytest --pyargs kros-core
#

from setuptools import setup, find_packages
from glob import glob
from os.path import basename
from os.path import splitext

# .........................................

NAME='kros-core'

with open('VERSION') as f:
    _version = f.read().strip()

with open('README.rst') as f:
    _long_description = f.read()

print('-- configuring: {}, version {}...\n'.format(NAME, _version))

setup(
    name=NAME,
    version=_version,
    description="Robot Operating System - Core, K-Series Robots",
    long_description=_long_description,
    long_description_content_type="text/x-rst",
    author='Ichiro Furusato',
    author_email='ichiro.furusato@gmail.com',
    url='https://github.com/ifurusato/kros-core',
    license='MIT',
    python_requires='>=3.8.0',
    package_dir={'': 'core'},
    packages=find_packages('core'),
    py_modules=[splitext(basename(path))[0] for path in glob('core/*.py')],
    include_package_data=True,
    install_requires=[
        'colorama',
        'numpy',
        'pytest',
        'psutil',
        'readchar',
        'pyyaml'
    ],
    test_suite='tests',
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Other OS',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Framework :: Robot Framework',
        'Framework :: Robot Framework :: Library',
        'Framework :: Robot Framework :: Tool',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords=[
        'robots', 'robotics'
    ],
)

print('-- complete.')

#EOF
