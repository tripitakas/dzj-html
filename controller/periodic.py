#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""
import logging
import pymongo
from controller.helper import prop
from datetime import datetime, timedelta
from controller.app import Application as App
from controller.task.base import TaskHandler as Th


def connect_db():
    cfg = App.load_config().get('database')
    if cfg.get('user'):
        uri = 'mongodb://{0}:{1}@{2}:{3}/admin'.format(
            cfg.get('user'), cfg.get('password'), cfg.get('host'), cfg.get('port', 27017)
        )
    else:
        uri = 'mongodb://{0}:{1}/'.format(cfg.get('host'), cfg.get('port', 27017))
    conn = pymongo.MongoClient(
        uri, connectTimeoutMS=2000, serverSelectionTimeoutMS=2000,
        maxPoolSize=10, waitQueueTimeoutMS=5000
    )
    return conn[cfg['name']]


def republish_timeout_tasks(db=None, timeout_days=None):
    """ 系统重新发布超时任务
        重新发布所有已领取未完成超过3天的任务
    """
    db = connect_db() if not db else db
    timeout_days = prop(App.load_config(), 'task.task_timeout') if timeout_days is None else timeout_days
    from_time = datetime.now() + timedelta(days=int(timeout_days))
    condition = {'status': Th.STATUS_PICKED, 'picked_time': {'$lt': from_time}}
    tasks = list(db.task.find(condition))
    for task in tasks:
        # 重新发布
        pre_tasks = task.get('pre_tasks') or {}
        for t in pre_tasks:
            pre_tasks[t] = ''
        update = {'status': Th.STATUS_OPENED, 'steps.submitted': None, 'pre_tasks': pre_tasks,
                  'picked_user_id': None, 'picked_by': None, 'picked_time': None, 'result': {}}
        r = db.task.update_one({'_id': task['_id']}, {'$set': update})
        if r.matched_count:
            add_op_log(db, 'republish', target_id=task['_id'], context=task['task_type'])

        # 释放领取任务时分配的数据锁
        shared_field = Th.get_shared_field(task['task_type'])
        if shared_field:
            Th.release_task_lock(db, [task['doc_id']], shared_field)


def release_timeout_lock(db=None, timeout_days=None):
    """ 系统释放超时的数据锁
        释放所有超过一天的临时数据锁
    """
    db = connect_db() if not db else db
    timeout_days = prop(App.load_config(), 'task.temp_lock_timeout') if timeout_days is None else timeout_days
    from_time = datetime.now() + timedelta(days=int(timeout_days))
    db.page.update_many({'lock.box.is_temp': True, 'lock.box.locked_time': {'$gt': from_time}},
                        {'$set': {'lock.box': dict()}})
    db.page.update_many({'lock.text.is_temp': True, 'lock.text.locked_time': {'$gt': from_time}},
                        {'$set': {'lock.text': dict()}})


def statistic_tasks(db=None):
    """ 统计每日完成的工作 """
    db = connect_db() if not db else db
    pass


def add_op_log(db, op_type, target_id, context):
    logging.info('%s,context=%s' % (op_type, context))
    db.log.insert_one(dict(type=op_type, target_id=target_id, context=context, create_time=datetime.now()))


def periodic_task(db, timeout_days=None):
    """ 定时任务，每晚11点运行"""
    republish_timeout_tasks(db, timeout_days)
    release_timeout_lock(db, timeout_days)
    statistic_tasks(db)


if __name__ == '__main__':
    import fire

    fire.Fire(periodic_task)
