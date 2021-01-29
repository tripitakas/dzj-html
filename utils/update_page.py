#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_page.py --uri=uri --func=init_variants
import re
import sys
import math
import json
import pymongo
from os import path, walk
from datetime import datetime
from operator import itemgetter

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.base import PageHandler as Ph


def update_box_log(page):
    for f in ['blocks', 'columns', 'chars']:
        boxes = page.get(f) or []
        for b in boxes:
            for k in ['x', 'y', 'w', 'h']:
                if b.get(k) and b[k] != round(b[k], 1):
                    b[k] = round(b[k], 1)
            if not b.get('box_logs'):
                continue
            for k in ['new', 'added', 'changed', 'updated']:
                if k in b:
                    b.pop(k, 0)
            if not len(b['box_logs']):
                b.pop('box_logs', 0)
            # 设置added/updated
            if b['box_logs'][0].get('username'):
                b['added'] = True
                if len(b['box_logs']) > 1:
                    b['changed'] = True
            else:
                b['changed'] = True
            # 设置log
            for i, log in enumerate(b['box_logs']):
                # 检查pos
                if log.get('x') and not log.get('pos'):
                    log['pos'] = {k: log[k] for k in ['x', 'y', 'w', 'h'] if log.get(k)}
                for k in ['x', 'y', 'w', 'h']:
                    log.pop(k, 0)
                # 检查op
                if i == 0:
                    if not log.get('username'):
                        log['op'] = 'initial'
                    else:
                        log['op'] = 'added'
                else:
                    log['op'] = 'changed'
                # 检查updated_time
                if log.get('updated_time'):
                    log['create_time'] = log['updated_time']
                    log.pop('updated_time', 0)
            # log按时间排序
            if len(b['box_logs']) > 1:
                if not b['box_logs'][0].get('create_time'):
                    b['box_logs'][0]['create_time'] = datetime.strptime('1999-1-1 00:00:00', '%Y-%m-%d %H:%M:%S')
                    b['box_logs'].sort(key=itemgetter('create_time'))
                    b['box_logs'][0].pop('create_time', 0)
                else:
                    b['box_logs'].sort(key=itemgetter('create_time'))
    return True


def update_page(db, fields=None):
    """ 更新page表（注：更新之前去掉updated字段"""
    size = 10
    # 更新1200标注数据，准备聚类校对
    cond = {'source': '1200标注数据', 'updated': None}
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    for i in range(page_count):
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i + 1, page_count))
        pages = list(db.page.find(cond, {k: 1 for k in ['name', 'chars']}).sort('_id', 1).skip(i * size).limit(size))
        for p in pages:
            print('[%s]%s' % (hp.get_date_time(), p['name']))
            if not p.get('chars'):
                continue
            for b in p.get('chars'):
                if 'cmb_txt' in fields:
                    b['cmb_txt'] = Ph.get_cmb_txt(b)
                if 'pc' in fields:
                    b['pc'] = Ph.get_prf_level(b)
                if 'sc' in fields:
                    b['sc'] = Ph.get_equal_level(b)
            db.page.update_one({'_id': p['_id']}, {'$set': {'chars': p['chars'], 'updated': True}})


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
