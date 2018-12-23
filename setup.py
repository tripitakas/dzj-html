#! /usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

import controller.app as meta

setup(name='dzj-api',
      version=meta.__version__,
      description='大藏经古籍数字化平台',
      keywords="大藏经,古籍数字化,tripitaka",
      platforms='any',
      packages=find_packages() + ['controller'],
      package_data={
          'controller': ['../main.py', '../*.yml', '../requirements.txt', '../run_tests.py', '../tox.ini']
      },
      classifiers=[
          'Intended Audience :: System Administrators',
          'Operating System :: OS Independent',
          'Natural Language :: Chinese (Simplified)',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.6',
          'Topic :: Text Processing',
          'Topic :: Text Processing :: Linguistic'
          ],
      zip_safe=False)
