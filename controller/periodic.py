#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import logging
from datetime import datetime, timedelta
from controller.task.base import TaskHandler as Th

data = {}
unlock_task_minutes = 60  # 一小时自动释放任务锁
unlock_temp_minutes = 30  # 30分钟自动释放数据锁


def periodic_task(app, opt=None):
    opt = opt or {}
    if 'update_time' not in data or opt.get('at_once') or (
            datetime.now() - data['update_time']).seconds > opt.get('interval', 600):
        data['update_time'] = datetime.now()
        try:
            task_time = datetime.now() - timedelta(minutes=opt.get('minutes', unlock_task_minutes))
            temp_time = datetime.now() - timedelta(minutes=opt.get('minutes', unlock_temp_minutes))
            # fields = list(set(Th.task_shared_data_fields.values()))
            fields = []  # to update
            task_cond = [{'lock.%s.locked_time' % f: {'$lt': task_time}, 'lock.%s.is_temp' % f: False} for f in fields]
            temp_cond = [{'lock.%s.locked_time' % f: {'$lt': temp_time}, 'lock.%s.is_temp' % f: True} for f in fields]
            for page in app.db.page.find({'$or': task_cond + temp_cond}):
                for field in fields:
                    lock = page['lock'].get(field)
                    if lock and lock.get('locked_time') and lock['locked_time'] < task_time:
                        task_type = lock['lock_type'].get('tasks')
                        locked_time = lock['locked_time'].strftime('%m-%d %H:%M')
                        update = {'lock.%s' % field: {}}
                        values = {'$set': update}
                        if not lock.get('is_temp'):
                            update['tasks.%s.status' % task_type] = Th.STATUS_OPENED
                            values['$unset'] = {}
                            for k in Th.prop(page, 'tasks.%s' % task_type):
                                if k.startswith('picked'):
                                    values['$unset'][k] = None
                        r = app.db.page.update_one({'name': page['name']}, values)
                        if r.matched_count:
                            add_op_log(app.db, 'auto_unlock', ','.join([
                                page['name'], locked_time, lock['locked_by'], task_type]))
        except Exception as e:
            logging.error('periodic_db_task: %s %s' % (e.__class__.__name__, str(e)))


def add_op_log(db, op_type, context):
    logging.info('%s,context=%s' % (op_type, context))
    db.log.insert_one(dict(type=op_type, context=context and context[:80], create_time=datetime.now()))
