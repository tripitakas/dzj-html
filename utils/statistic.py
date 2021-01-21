#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import pymongo
from os import path
from datetime import datetime


def statistic_task(db, dst_dir):
    """ 统计用户工作量"""
    head = ['页编码', '字框数据', '领取时间', '完成时间', '执行秒数']
    fields = ['doc_id', 'char_count', 'picked_time', 'finished_time', 'used_time']
    head2 = ['日期', '姓名', '任务总数', '字框总数', '有效任务数', '有效执行时间', '秒/任务', '任务/分钟']
    fields2 = ['data', 'name', 'task_count', 'char_count', 'valid_count', 'valid_time', 'speed1', 'speed2']
    daily = []
    users = list(db.user.find({'group': '全职校对人员'}, {'name': 1}))
    for u in users:
        print('process ' + u['name'])
        for i in range(14, 19):
            start = datetime.strptime('2020-12-%s' % i, '%Y-%m-%d')
            end = datetime.strptime('2020-12-%s' % (i + 1), '%Y-%m-%d')
            cond = {'task_type': 'cut_proof', 'picked_user_id': u['_id'], 'status': 'finished',
                    'picked_time': {'$gt': start, '$lt': end}}
            tasks = list(db.task.find(cond, {k: 1 for k in fields}).sort('picked_time', 1))
            for t in tasks:
                t['used_time'] = (t['finished_time'] - t['picked_time']).seconds
                t['picked_time'] = t['picked_time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                t['finished_time'] = t['finished_time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            valid = [t for t in tasks if t['used_time'] < 60 * 4]
            valid_time = sum([t['used_time'] for t in valid])
            daily.append({'data': '2020-12-%s' % i, 'name': u['name'], 'task_count': len(tasks),
                          'valid_count': len(valid), 'valid_time': valid_time,
                          'char_count': sum([t['char_count'] for t in tasks]),
                          'speed1': round(valid_time / len(valid), 2),
                          'speed2': round(len(valid) / valid_time * 60, 2)})
            # 用户的任务详情
            with open(path.join(dst_dir, '%s.csv' % u['name']), 'w', newline='') as fn:
                writer = csv.writer(fn)
                writer.writerow(head)
                writer.writerows([[t.get(f) for f in fields] for t in tasks])
    # 用户任务统计情况
    with open(path.join(dst_dir, '日均统计.csv'), 'w', newline='') as fn:
        writer = csv.writer(fn)
        writer.writerow(head2)
        writer.writerows([[d.get(f) for f in fields2] for d in daily])


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
