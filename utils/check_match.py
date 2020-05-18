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


def check_match(db=None, db_name='tripitaka', uri='localhost', condition=None, page_names=None,
                fields=None, publish_task=True, username=None):
    """ 检查图文是否匹配
    :param fields 检查哪个字段，包括cmp_txt/ocr_col/txt
    :param publish_task，如果图文不匹配，是否发布相关任务
    """
    db = db or pymongo.MongoClient(uri)[db_name]
    if page_names:
        page_names = page_names.split(',') if isinstance(page_names, str) else page_names
        condition = {'name': {'$in': page_names}}
    elif isinstance(condition, str):
        condition = json.loads(condition)
    elif not condition:
        condition = {}

    once_size = 50
    fields = ['ocr_col', 'cmp_txt', 'txt'] if not fields else fields.split(',') if isinstance(fields, str) else fields
    total_count = db.page.count_documents(condition)
    log_id = Bh.add_op_log(db, 'check_match', 'ongoing', [], username)
    for i in range(int(math.ceil(total_count / once_size))):
        match, mis_match = [], []
        pages = list(db.page.find(condition).skip(i * once_size).limit(once_size))
        for page in pages:
            print('[%s] processing %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), page['name']))
            update, chars, changed = dict(), page['chars'], False
            for field in fields:
                if not Ph.get_txt(page, field):
                    continue
                if hp.prop(page, 'txt_match.' + field) is True:
                    match.append([page['name'], field])
                    continue
                r = Ph.check_match(page['chars'], Ph.get_txt(page, field))
                if r['status'] is True:
                    changed = True
                    match.append([page['name'], field])
                    Ph.write_back_txt(chars, Ph.get_txt(page, field), field)
                    update.update({'txt_match.' + field: True})
                else:
                    mis_match.append([page['name'], field])
                    update.update({'txt_match.' + field: False})
            if changed:
                update.update({'chars': chars})
            db.page.update_one({'_id': page['_id']}, {'$set': update})
        log = dict(match=match, mis_match=mis_match)
        db.oplog.update_one({'_id': log_id}, {'$addToSet': {'content': {k: v for k, v in log.items() if v}}})
    db.oplog.update_one({'_id': log_id}, {'$set': {'status': 'finished'}})


if __name__ == '__main__':
    import fire

    fire.Fire(check_match)
