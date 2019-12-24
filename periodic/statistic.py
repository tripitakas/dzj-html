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
from controller.task.base import TaskHandler as Th
from periodic.worker import Worker


def day_begin(dt):
    return datetime.strptime(dt.strftime('%Y-%m-%d'), '%Y-%m-%d')


class StatisticTasks(Worker):
    def __init__(self, db):
        Worker.__init__(self, db)

    def work(self, **kwargs):
        def statistic():
            ret = []
            user_id, task_type, count = tasks[0]['picked_user_id'], tasks[0]['task_type'], 1
            for task in tasks[1:]:
                if task['task_type'] == task_type and task['picked_user_id'] == user_id:
                    count += 1
                else:
                    ret.append(dict(day=from_day, user_id=user_id, task_type=task_type, count=count))
                    user_id, task_type, count = task['picked_user_id'], task['task_type'], 1
            ret.append(dict(day=from_day, user_id=user_id, task_type=task_type, count=count))
            return ret

        latest_stat = self.db.statistic.find_one({}, sort=[('day', -1)])
        first_task = self.db.task.find_one({'status': Th.STATUS_FINISHED}, sort=[('finished_time', -1)])
        if not first_task:
            return

        result, today = [], day_begin(datetime.now())
        from_day = day_begin(latest_stat['day'] if latest_stat else first_task['finished_time'])
        while from_day < today:
            condition = {'finished_time': {'$gt': from_day, '$lt': from_day + timedelta(days=1)}}
            tasks = list(self.db.task.find(condition).sort([('task_type', 1), ('picked_user_id', 1)]))
            if tasks:
                result.extend(statistic())
            from_day = from_day + timedelta(days=1)

        if result:
            self.db.statistic.insert_many(result)


def statistic_tasks(db=None, uri='localhost', db_name='tripitaka', once_break=False, interval=3600 * 12):
    """
    统计每人每日完成的不同类型工作的数量，格式为dict(day='', user_id='', task_type='', count='')
    :param db: 数据库连接对象，为空则根据 uri 和 db_name 自动连接
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    :param db_name: 数据库名
    :param once_break: 处理一次后是否退出
    :param interval: 任务间隔的休息时间
    """
    if not db:
        conn = pymongo.MongoClient(uri)
        db = conn[db_name]
    worker = StatisticTasks(db)
    return worker.run(once_break=once_break, interval=interval)


if __name__ == '__main__':
    import fire

    fire.Fire(statistic_tasks)
