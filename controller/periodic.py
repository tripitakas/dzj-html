#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import logging
from datetime import datetime

data = {}


def periodic_task(app):
    if 'update_time' not in data or (datetime.now() - data['update_time']).seconds > 1800:
        data['update_time'] = datetime.now()
        try:
            pass
        except Exception as e:
            logging.error('periodic_db_task: %s %s' % (e.__class__.__name__, str(e)))
