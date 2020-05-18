#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import math
import pymongo
from os import path
from datetime import datetime

BASE_DIR = path.dirname(path.dirname(path.dirname(__file__)))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.base import BaseHandler as Bh
from controller.page.base import PageHandler as Ph


def check_match(db=None, db_name='tripitaka', uri='localhost', field=None,
                condition=None, page_names=None, username=None):
    """ 检查图文是否匹配"""
    db = db or pymongo.MongoClient(uri)[db_name]
    if page_names:
        page_names = page_names.split(',') if isinstance(page_names, str) else page_names
        condition = {'name': {'$in': page_names}}
    elif isinstance(condition, str):
        condition = json.loads(condition)
    elif not condition:
        condition = {}

    once_size = 50
    total_count = db.page.count_documents(condition)
    log_id = Bh.add_op_log(db, 'check_match', 'ongoing', [], username)
    for i in range(int(math.ceil(total_count / once_size))):
        match, mis_match, matched_before = [], [], []
        pages = list(db.page.find(condition).skip(i * once_size).limit(once_size))
        for page in pages:
            print('[%s] processing %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), page['name']))
            if hp.prop(page, 'txt_match.' + field) is True:
                matched_before.append(page['name'])
                continue
            r = Ph.check_match(page['chars'], Ph.get_txt(page, field))
            if r['status'] is True:
                match.append(page['name'])
                chars = Ph.write_back_txt(page['chars'], Ph.get_txt(page, field), field)
                db.page.update_one({'_id': page['_id']}, {'$set': {'chars': chars, 'txt_match.' + field: True}})
            else:
                mis_match.append(page['name'])
                db.page.update_one({'_id': page['_id']}, {'$set': {'txt_match.' + field: False}})
        log = dict(match=match, mis_match=mis_match, matched_before=matched_before)
        db.oplog.update_one({'_id': log_id}, {'$addToSet': {'content': {k: v for k, v in log.items() if v}}})
    db.oplog.update_one({'_id': log_id}, {'$set': {'status': 'finished'}})


if __name__ == '__main__':
    import fire

    fire.Fire(check_match)
