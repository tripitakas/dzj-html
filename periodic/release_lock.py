#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""
import sys
import pymongo
from os import path
from controller.helper import prop
from datetime import datetime, timedelta

sys.path.append(path.dirname(path.dirname(__file__)))
from periodic.worker import Worker
from controller.helper import load_config


class ReleaseTimeoutLock(Worker):
    def __init__(self, db):
        Worker.__init__(self, db)

    def work(self, timeout_hours=None, **kwargs):
        if not timeout_hours:
            timeout_hours = prop(load_config(), 'task.temp_lock_timeout_hours', 1)
        from_time = datetime.now() - timedelta(hours=int(timeout_hours))
        self.db.page.update_many({'lock.box.is_temp': True, 'lock.box.locked_time': {'$lt': from_time}},
                                 {'$set': {'lock.box': dict()}})
        self.db.page.update_many({'lock.text.is_temp': True, 'lock.text.locked_time': {'$lt': from_time}},
                                 {'$set': {'lock.text': dict()}})


def release_timeout_lock(db=None, uri='localhost', db_name='tripitaka', timeout_hours=None,
                         once_break=False, interval=3600):
    """
    释放超时的临时数据锁
    :param db: 数据库连接对象，为空则根据 uri 和 db_name 自动连接
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    :param db_name: 数据库名
    :param timeout_hours: 超时时间
    :param once_break: 处理一次后是否退出
    :param interval: 任务间隔的休息时间
    """
    if not db:
        conn = pymongo.MongoClient(uri)
        db = conn[db_name]
    worker = ReleaseTimeoutLock(db)
    return worker.run(once_break=once_break, interval=interval, timeout_hours=timeout_hours)


if __name__ == '__main__':
    import fire

    fire.Fire(release_timeout_lock)
