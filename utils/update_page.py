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


def reset_variant(page):
    changed = False
    for c in page.get('chars') or []:
        if len(c.get('txt') or '') > 1 and c['txt'][0] == 'Y':
            c['txt'] = 'v' + hp.dec2code36(int(c['txt'][1:]))
            changed = True
    return changed


def reset_txt_type(page):
    # txt_types = {'Y': '没问题', 'M': '模糊或残损', 'N': '不确定', '*': '不认识'}
    changed = False
    for c in page.get('chars') or []:
        # reset char
        txt_type = c.pop('txt_type', 0)
        if txt_type == 'M':
            c['is_vague'] = True
        elif txt_type in ['N', '*']:
            c['uncertain'] = True
        # reset logs
        for log in c.get('txt_logs') or []:
            changed = True
            txt_type = log.pop('txt_type', 0)
            if txt_type == 'M':
                log['is_vague'] = True
            elif txt_type in ['N', '*']:
                log['uncertain'] = True
    return changed


def reset_ocr_pos(page):
    changed = False
    for f in ['blocks', 'columns', 'chars']:
        boxes = page.get(f) or []
        for b in boxes:
            for k in ['x', 'y', 'w', 'h']:
                if b.get(k) and b[k] != round(b[k], 1):
                    changed = True
                    b[k] = round(b[k], 1)
    return changed


def reset_ocr_txt(page):
    changed = False
    for c in page.get('chars') or []:
        c['ocr_txt'] = Ph.get_cmb_txt(c)
        txts = [c[k] for k in ['ocr_txt', 'ocr_col', 'cmp_txt'] if c.get(k)]
        c.get('alternatives') and txts.append(c.get('alternatives')[:1])
        if not c.get('txt_logs') and (not c.get('txt') or c['txt'] in txts):
            changed = True
            c['txt'] = c['ocr_txt']
    return changed


def reset_box_log(page):
    for f in ['blocks', 'columns', 'chars']:
        boxes = page.get(f) or []
        for b in boxes:
            for k in ['new', 'added', 'changed', 'updated']:
                b.pop(k, 0)
            if not b.get('box_logs'):
                continue
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


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    """ 更新page表
        注：更新之前去掉updated字段
    """
    size, i = 1000, 0
    cond = {'updated': None}
    db = pymongo.MongoClient(uri)[db_name]
    item_count = db.page.count_documents(cond)
    page_count = math.ceil(item_count / size)
    print('[%s]%s items, %s pages' % (hp.get_date_time(), item_count, page_count))
    while db.page.find_one(cond):
        i += 1
        print('[%s]processing page %s / %s' % (hp.get_date_time(), i, page_count))
        fields = ['name', 'blocks', 'columns', 'chars']
        pages = list(db.page.find(cond, {k: 1 for k in fields}).limit(size))
        for p in pages:
            print('[%s]%s' % (hp.get_date_time(), p['name']))
            r = eval(func)(p, **kwargs)
            update = {'updated': True}
            r and update.update({k: p[k] for k in ['blocks', 'columns', 'chars'] if p.get(k)})
            db.page.update_one({'_id': p['_id']}, {'$set': update})


if __name__ == '__main__':
    import fire

    fire.Fire(main)
