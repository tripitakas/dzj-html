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
    cond = {'task_type': {'$in': ['cut_proof', 'cut_review']}}
    item_count = db.task.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        fields = ['doc_id', 'task_type', 'picked_user_id']
        tasks = list(db.task.find(cond, {k: 1 for k in fields}).sort('_id', 1).skip(i * size).limit(size))
        for t in tasks:
            print('[%s]%s, %s' % (hp.get_date_time(), t['task_type'], t['doc_id']))
            page = db.page.find_one({'name': t['doc_id']})
            if not page:
                invalid.append(t['doc_id'])
                continue
            op_no = Ph.get_user_op_no(page, t['picked_user_id'])
            db.task.update_one({'_id': t['_id']}, {'$set': op_no})
    if invalid:
        print('invalid: %s' % invalid)


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
