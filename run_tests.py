#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Usage:
# python -m run_tests.py --coverage
# python -m run_tests.py -k test_case_name

import os
import sys
import pytest

sys.path.append(os.path.dirname(__file__))

if __name__ == '__main__':
    test_args = sys.argv[1:]

    # Logic to run pytest with coverage turned on
    try:
        test_args.remove('--coverage')
    except ValueError:
        test_args += ['tests']
        # test_args += ['-k test_api_change_my_profile']
    else:
        test_args = ['--cov=controller',
                     '--cov-report=term',
                     '--cov-report=html',
                     'tests'] + test_args
    errcode = pytest.main(test_args)
    sys.exit(errcode)
