#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_task.py --uri=uri --func=
# 更新数据库task表

import re
import sys
import math
import json
import pymongo
from os import path, walk
from datetime import datetime
from operator import itemgetter
from functools import cmp_to_key
from bson.objectid import ObjectId

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.base import PageHandler as Ph
from controller.char.base import CharHandler as Ch


def update_used_time(db):
    """更新任务-执行时间"""
    size = 10000
    task_types = ['cut_proof', 'cut_review', 'cluster_proof', 'cluster_review']
    cond = {'task_type': {'$in': task_types}, 'status': 'finished'}
    item_count = db.task.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['picked_time', 'finished_time']
        tasks = list(db.task.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for t in tasks:
            used_time = (t['finished_time'] - t['picked_time']).total_seconds()
            db.task.update_one({'_id': t['_id']}, {'$set': {'used_time': used_time}})


def update_op_no(db):
    """更新切分任务-用户操作历史"""
    size = 100
    invalid = []
    cond = {'task_type': {'$in': ['cut_proof', 'cut_review']}, 'status': 'finished'}
    item_count = db.task.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['doc_id', 'task_type', 'picked_user_id', 'picked_time', 'finished_time']
        tasks = list(db.task.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for t in tasks:
            print('[%s]%s, %s' % (hp.get_date_time(), t['task_type'], t['doc_id']))
            if not t.get('picked_user_id'):
                continue
            page = db.page.find_one({'name': t['doc_id']})
            if not page:
                invalid.append(t['doc_id'])
                continue
            update = Ph.get_user_op_no(page, t['picked_user_id'])
            db.task.update_one({'_id': t['_id']}, {'$set': update})
    if invalid:
        print('invalid: %s' % invalid)


def update_txt_equals(db, batch='', task_type=''):
    """ 更新聚类任务-相同程度"""
    Ch.update_txt_equals(db, batch, task_type)


def check_cluster_task(db, char_source='', task_type='', batch=''):
    """ 检查某分类数据的聚类校对任务的字种、字数是否变化"""
    # 统计字种及字数
    base_field = Ch.get_base_field(task_type)
    counts = list(db.char.aggregate([
        {'$match': {'source': char_source}}, {'$group': {'_id': '$' + base_field, 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]))
    counts = {c['_id']: dict(count=c['count']) for c in counts}
    # 检查是否发生了变化
    changed, debug = [], True
    cond = {'batch': batch, 'task_type': task_type}
    tasks = list(db.task.find(cond, {'base_txts': 1, 'params': 1, 'task_type': 1, 'char_count': 1}))
    for task in tasks:
        base_txts, equal = task['base_txts'], True
        for item in base_txts:
            txt, count = item['txt'], item['count']
            if counts.get(txt):
                counts[txt]['active'] = True
                item['active'] = True
                if count != counts[txt]['count']:
                    item['old_count'] = count
                    item['count'] = counts[txt]['count']
                    changed.append(item)
                    equal = False
        base_txts = [dict(txt=t['txt'], count=t['count']) for t in base_txts if t.get('active')]
        char_count = sum([t['count'] for t in base_txts])
        if not equal or char_count != task.get('char_count'):
            db.task.update_one({'_id': task['_id']}, {'$set': {'base_txts': base_txts, 'char_count': char_count}})

    # 任务聚类字种的字数发生了改变
    debug and print(changed)
    # 该批次任务中，尚未使用的字种（需要发布新的任务）
    debug and print(['%s:%s' % (k, v['count']) for k, v in counts.items() if not v.get('active')])


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished')
