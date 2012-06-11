#!/usr/bin/env python

import os
import sys

sys.path.insert(0, os.path.abspath('lib'))
from libssh import __version__, __author__
from distutils.core import setup

setup(name='libssh',
      version=__version__,
      description='Python wrapper for libssh (libssh.org).',
      author=__author__,
      author_email='mgwilliams@gmail.com',
      url='http://wwwgithub.com/mgwilliams/python-libssh/',
      license='GPLv3',
      package_dir={ 'libssh': 'lib/libssh' },
      packages=[
         'libssh',
      ],
)
