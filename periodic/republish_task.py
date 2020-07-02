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
from periodic.worker import Worker
from controller import helper as hp
from controller.task.base import TaskHandler as Th


class RepublishTimeoutTasks(Worker):
    def __init__(self, db):
        Worker.__init__(self, db)

    def work(self, timeout_days=None, **kwargs):
        # 重新发布任务
        timeout_days = hp.prop(hp.load_config(), 'task.task_timeout_days', 1) if not timeout_days else timeout_days
        from_time = datetime.now() - timedelta(days=int(timeout_days))
        tasks = list(self.db.task.find({'status': Th.STATUS_PICKED, 'picked_time': {'$lt': from_time}}))
        cond = {'_id': {'$in': [t['_id'] for t in tasks]}}
        self.db.task.update_many(cond, {'$set': {'status': 'published'}})
        self.db.task.update_many(cond, {'$unset': {
            'picked_time': '', 'picked_by': '', 'picked_user_id': ''
        }})
        cond['steps.submitted'] = {'$exists': True}
        self.db.task.update_many(cond, {'$unset': {'steps.submitted': ''}})
        # 重置page表的tasks字段
        for t in tasks:
            if t.get('collection') == 'page' and t.get('doc_id'):
                self.db.page.update_one({'name': t['doc_id']}, {'$set': {
                    'tasks.%s.%s' % (t.get('task_type'), t.get('num', 1)): Th.STATUS_PUBLISHED
                }})
        self.add_log('republish_task', [t['_id'] for t in tasks])


def republish_timeout_tasks(db=None, uri='localhost', db_name='tripitaka', timeout_days=None,
                            once_break=False, interval=3600 * 12):
    """ 重新发布进行中的超时任务
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
