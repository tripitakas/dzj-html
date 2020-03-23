#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import math
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(path.dirname(__file__)))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.base import BaseHandler as Bh


def gen_chars(db=None, db_name='tripitaka', uri='localhost', reset=True,
              condition=None, page_names=None, username=None):
    """ 从页数据中导出字数据"""

    def is_changed(a, b):
        """ 检查坐标和字序是否发生变化"""
        for k in ['char_id']:
            if a[k] != b[k]:
                return True
        for k in ['x', 'y', 'w', 'h']:
            if a['pos'][k] != b['pos'][k]:
                return True
        return False

    db = db or pymongo.MongoClient(uri)[db_name]
    if reset:
        db.char.delete_many({})

    if page_names:
        page_names = page_names.split(',') if isinstance(page_names, str) else page_names
        condition = {'name': {'$in': page_names}}
    elif isinstance(condition, str):
        condition = json.loads(condition)
    elif not condition:
        condition = {}

    once_size = 50
    total_count = db.page.count_documents(condition)
    fields = ['name', 'source', 'columns', 'chars']
    for i in range(int(math.ceil(total_count / once_size))):
        pages = list(db.page.find(condition, {k: 1 for k in fields}).skip(i * once_size).limit(once_size))
        # 查找、分类chars
        chars, invalid_chars, invalid_pages = [], [], []
        for p in pages:
            try:
                id2col = {col['column_id']: {k: col[k] for k in ['cid', 'x', 'y', 'w', 'h']} for col in p['columns']}
                for c in p['chars']:
                    try:
                        meta = dict(page_name=p['name'])
                        meta['name'] = '%s_%s' % (p['name'], c['cid'])
                        meta.update(
                            {k: c[k] for k in ['source', 'cid', 'char_id', 'ocr_txt', 'alternatives'] if c.get(k)})
                        meta.update({k: int(c[k] * 1000) for k in ['cc', 'sc'] if c.get(k)})
                        meta['txt'] = c.get('txt') or c.get('ocr_txt')
                        meta['pos'] = dict(x=c['x'], y=c['y'], w=c['w'], h=c['h'])
                        meta['column'] = id2col.get('b%sc%s' % (c['block_no'], c['column_no']))
                        meta['uid'] = hp.align_code('%s_%s' % (p['name'], c['char_id'][1:].replace('c', '_')))
                        chars.append(meta)
                    except KeyError:
                        invalid_chars.append('%s_%s' % (p['name'], c['cid']))
            except KeyError:
                invalid_pages.append(p['name'])
        # 更新已存在的chars
        chars_dict = {c['name']: c for c in chars}
        existed = list(db.char.find({'name': {'$in': [c['name'] for c in chars]}}))
        print('update existed %s records: %s' % (len(existed), ','.join([c['name'] for c in existed])))
        for e in existed:
            c = chars_dict.get(e['name'])
            if is_changed(e, c):
                db.char.update_one({'_id': e['_id']}, {'$set': {k: c.get(k) for k in ['char_id', 'uid', 'pos']}})
        # 插入不存在的chars
        existed_id = [c['name'] for c in existed]
        un_existed = [c for c in chars if c['name'] not in existed_id]
        if un_existed:
            db.char.insert_many(un_existed, ordered=False)
        print('insert new %s records: %s' % (len(un_existed), ','.join([c['name'] for c in un_existed])))
        log = dict(inserted_char=[c['name'] for c in un_existed], existed_char=[c['name'] for c in existed],
                   invalid_char=invalid_chars, invalid_pages=invalid_pages)
        Bh.add_op_log(db, 'gen_chars', log, username)


if __name__ == '__main__':
    import fire

    fire.Fire(gen_chars)
