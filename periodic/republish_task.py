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
from controller.app import Application as App
from controller.task.base import TaskHandler as Th
from periodic.worker import Worker


class RepublishTimeoutTasks(Worker):
    def __init__(self, db):
        Worker.__init__(self, db)

    def work(self, timeout_days=None, **kwargs):
        if not timeout_days:
            timeout_days = prop(App.load_config(), 'task.task_timeout_days', 1)
        from_time = datetime.now() - timedelta(days=int(timeout_days))
        condition = {'status': Th.STATUS_PICKED, 'picked_time': {'$lt': from_time}}
        tasks = list(self.db.task.find(condition))
        for task in tasks:
            # 重新发布任务
            pre_tasks = {p: '' for p in prop(task, 'pre_tasks', {})}
            self.db.task.update_one({'_id': task['_id']}, {'$set': {
                'status': Th.STATUS_PUBLISHED, 'steps.submitted': [], 'pre_tasks': pre_tasks,
                'picked_user_id': None, 'picked_by': None, 'picked_time': None, 'result': {}
            }})
            self.add_log('republish', target_id=task['_id'], context=task['task_type'])

            # 释放数据锁
            shared_field = Th.get_shared_field(task['task_type'])
            if shared_field:
                update = {'lock.%s' % shared_field: dict()}
                id_name = prop(Th.data_auth_maps, shared_field + '.id')
                collection = prop(Th.data_auth_maps, shared_field + '.collection')
                self.db[collection].update_many({id_name: task['doc_id']}, {'$set': update})


def republish_timeout_tasks(db=None, uri='localhost', db_name='tripitaka', timeout_days=None,
                            once_break=False, interval=3600*12):
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
