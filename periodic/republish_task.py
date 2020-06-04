#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""
import sys
import pymongo
from os import path
from datetime import datetime, timedelta

sys.path.append(path.dirname(path.dirname(__file__)))
from controller.helper import prop
from controller.task.base import TaskHandler as Th
from periodic.worker import Worker
from controller.helper import load_config


class RepublishTimeoutTasks(Worker):
    def __init__(self, db):
        Worker.__init__(self, db)

    def work(self, timeout_days=None, **kwargs):
        if not timeout_days:
            timeout_days = prop(load_config(), 'task.task_timeout_days', 1)
        from_time = datetime.now() - timedelta(days=int(timeout_days))
        tasks = list(self.db.task.find({'status': Th.STATUS_PICKED, 'picked_time': {'$lt': from_time}}))
        for task in tasks:
            # 重新发布任务
            pre_tasks = {p: '' for p in prop(task, 'pre_tasks', {})}
            self.db.task.update_one({'_id': task['_id']}, {'$set': {
                'status': Th.STATUS_PUBLISHED, 'steps.submitted': [], 'pre_tasks': pre_tasks,
                'picked_user_id': None, 'picked_by': None, 'picked_time': None, 'result': {}
            }})
            self.add_log('republish_task', task['_id'],
                         dict(task_type=task['task_type'], doc_id=task.get('doc_id') or ''))


def republish_timeout_tasks(db=None, uri='localhost', db_name='tripitaka', timeout_days=None,
                            once_break=False, interval=3600 * 12):
    """
    重新发布超时任务
    :param db: 数据库连接对象，为空则根据 uri 和 db_name 自动连接
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    :param db_name: 数据库名
    :param timeout_days: 超时时限
    :param once_break: 处理一次后是否退出
    :param interval: 任务间隔的休息时间
    """
    if not db:
        conn = pymongo.MongoClient(uri)
        db = conn[db_name]
    worker = RepublishTimeoutTasks(db)
    return worker.run(once_break=once_break, interval=interval, timeout_days=timeout_days)


if __name__ == '__main__':
    import fire

    fire.Fire(republish_timeout_tasks)
