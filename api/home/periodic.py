#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/10/23
"""

import logging
from datetime import datetime

data = {}


def periodic_task(app):
    if 'update_time' not in data or (datetime.now() - data['update_time']).seconds > 1800:
        data['update_time'] = datetime.now()
        try:
            conn = app.open_connection()
            try:
                conn.commit()
            except Exception as e:
                logging.error('periodic_task: ' + str(e))
                conn.rollback()
            finally:
                conn.close()
        except Exception as e:
            logging.error('periodic_db_task: %s %s' % (e.__class__.__name__, str(e)))

        try:
            app.remove_idle_channels()
        except Exception as e:
            logging.error('periodic_task: %s %s' % (e.__class__.__name__, str(e)))
