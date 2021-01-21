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


def update_page_task(db):
    """更新页任务"""
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
            # op no
            update = Ph.get_user_op_no(page, t['picked_user_id'])
            # exe time
            update['exe_time'] = (t['finished_time'] - t['picked_time']).seconds
            db.task.update_one({'_id': t['_id']}, {'$set': update})
    if invalid:
        print('invalid: %s' % invalid)


def update_char_task(db, batch='', reset=False):
    """ 更新聚类任务-需要校对字数"""
    size = 1000
    cond = {'task_type': {'$regex': 'cluster_'}}
    batch and cond.update({'batch': batch})
    not reset and cond.update({'required_count': None})
    cnt = db.task.count_documents(cond)
    page_count = math.ceil(cnt / size)
    print('[%s]%s tasks to process' % (hp.get_date_time(), cnt))
    for i in range(page_count):
        field = 'ocr_txt'
        tasks = list(db.task.find(cond, {'params': 1}).sort('_id', 1).skip(i * size).limit(size))
        print('[%s]processing task %s/%s' % (hp.get_date_time(), i + 1, page_count))
        for task in tasks:
            params = task['params']
            txt_kinds = [p[field] for p in params if p.get(field)]
            cond2 = {field: {'$in': txt_kinds}, 'source': params[0]['source'], 'un_required': {'$ne': True}}
            required_count = db.char.count_documents(cond2)
            db.task.update_one({'_id': task['_id']}, {'$set': {'required_count': required_count}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
