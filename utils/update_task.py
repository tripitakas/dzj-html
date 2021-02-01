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


def update_txt_equals(db, batch='', cond=None):
    """ 更新聚类任务-相同程度"""
    size = 1000
    cond = cond or {'task_type': {'$regex': 'cluster_'}, 'batch': batch}
    item_count = db.task.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s tasks to process' % (hp.get_date_time(), item_count))
    for i in range(page_count):
        project = {'base_txts': 1, 'params': 1, 'task_type': 1}
        tasks = list(db.task.find(cond, project).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing page %s/%s' % (hp.get_date_time(), i + 1, page_count))
        for task in tasks:
            source = hp.prop(task, 'params.source')
            b_field = Ch.get_base_field(task['task_type'])
            b_txts = [t[b_field] for t in task['base_txts']]
            counts = list(db.char.aggregate([
                {'$match': {'source': source, b_field: {'$in': b_txts}}},
                {'$group': {'_id': '$sc', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            txt_equals = {str(c['_id']): c['count'] for c in counts}
            db.task.update_one({'_id': task['_id']}, {'$set': {'txt_equals': txt_equals}})


def main(db_name='tripitaka', uri='localhost', func='update_txt_equals', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
