#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 将page['chars']中的数据同步到char表，包括增删改等
# 数据同步时，检查字框的char_id字序信息和x/y/w/h等位置信息，如果发生了改变，则进行同步
# python3 utils/extract_img.py --condition= --user_name=

import sys
import json
import math
import pymongo
from os import path
from datetime import datetime

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.char.char import Char
from controller.char.base import CharHandler


def is_changed(a, b):
    """ 检查坐标和字序是否发生变化"""
    if a['char_id'] != b['char_id']:
        return True
    for k in ['x', 'y', 'w', 'h']:
        if a['pos'][k] != b['pos'][k]:
            return True
    for k in ['x', 'y', 'w', 'h', 'cid']:
        if not a.get('column') or not b.get('column'):
            return True
        if a['column'][k] != b['column'][k]:
            return True
    return False


def gen_chars(db=None, db_name=None, uri=None, condition=None, page_names=None, username=None):
    """ 从页数据中导出字数据"""
    cfg = hp.load_config()
    db = db or (uri and pymongo.MongoClient(uri)[db_name]) or hp.connect_db(cfg['database'], db_name=db_name)[0]
    # condition
    if page_names:
        page_names = page_names.split(',') if isinstance(page_names, str) else page_names
        condition = {'name': {'$in': page_names}}
    elif isinstance(condition, str):
        condition = json.loads(condition)
    elif not condition:
        condition = {}
    # process
    once_size = 300
    total_count = db.page.count_documents(condition)
    print('[%s]start gen chars, condition=%s, count=%s' % (hp.get_date_time(), condition, total_count))
    fields1 = ['name', 'source', 'columns', 'chars']
    fields2 = ['source', 'cid', 'char_id', 'txt', 'ocr_txt', 'ocr_col', 'cmp_txt', 'alternatives']
    for i in range(int(math.ceil(total_count / once_size))):
        pages = list(db.page.find(condition, {k: 1 for k in fields1}).skip(i * once_size).limit(once_size))
        p_names = [p['name'] for p in pages]
        print('[%s]processing %s' % (hp.get_date_time(), ','.join(p_names)))
        # 查找、分类chars
        chars, char_names, invalid_chars, invalid_pages, valid_pages = [], [], [], [], []
        for p in pages:
            try:
                id2col = {col['column_id']: {k: col[k] for k in ['cid', 'x', 'y', 'w', 'h']} for col in p['columns']}
                for c in p['chars']:
                    try:
                        if c.get('deleted'):
                            continue
                        char_names.append('%s_%s' % (p['name'], c['cid']))
                        m = dict(page_name=p['name'], source=p.get('source'), txt_level=0, img_need_updated=True)
                        m['name'] = '%s_%s' % (p['name'], c['cid'])
                        m.update({k: c[k] for k in fields2 if c.get(k)})
                        m.update({k: int((c.get(k) or 0) * 1000) for k in ['cc', 'lc']})
                        m['ocr_txt'] = (c.get('alternatives') or '')[:1]
                        m['ocr_col'] = c.get('ocr_col') or '■'
                        m['cmb_txt'] = Char.get_cmb_txt(c)
                        m['txt'] = c.get('txt') or m['cmb_txt']
                        m['sc'] = Char.get_equal_level(c)
                        m['pc'] = Char.get_prf_level(c)
                        m['pos'] = dict(x=c['x'], y=c['y'], w=c['w'], h=c['h'])
                        c['column_no'] = c.get('column_no') or c.pop('line_no')
                        m['column'] = id2col.get('b%sc%s' % (c['block_no'], c['column_no']))
                        m['uid'] = hp.align_code('%s_%s' % (p['name'], c['char_id'][1:].replace('c', '_')))
                        chars.append(m)
                    except KeyError as e:
                        print(e)
                        invalid_chars.append('%s_%s' % (p['name'], c['cid']))
                valid_pages.append(p['name'])
            except KeyError:
                invalid_pages.append(p['name'])

        # 删除多余的chars
        deleted = list(db.char.find({'page_name': {'$in': p_names}, 'name': {'$nin': char_names}}, {'name': 1}))
        if deleted:
            db.char.delete_many({'_id': {'$in': [d['_id'] for d in deleted]}})
            print('delete %s records: %s' % (len(deleted), ','.join([c['name'] for c in deleted])))
        # 更新已存在的chars。检查和更新char_id、uid、pos三个字段
        chars_dict = {c['name']: c for c in chars}
        existed = list(db.char.find({'name': {'$in': [c['name'] for c in chars]}}))
        if existed:
            changed = []
            for e in existed:
                c = chars_dict.get(e['name'])
                if is_changed(e, c):
                    changed.append(c['name'])
                    update = {k: c[k] for k in ['char_id', 'uid', 'pos', 'column'] if c.get(k)}
                    db.char.update_one({'_id': e['_id']}, {'$set': {**update, 'img_need_updated': True}})
            if changed:
                print('update changed %s records: %s' % (len(changed), ','.join([c for c in changed])))
        # 插入不存在的chars
        existed_id = [c['name'] for c in existed]
        un_existed = [c for c in chars if c['name'] not in existed_id]
        if un_existed:
            db.char.insert_many(un_existed, ordered=False)
            print('insert new %s records: %s' % (len(un_existed), ','.join([c['name'] for c in un_existed])))
        # 更新page表的has_gen_chars字段
        db.page.update_many({'name': {'$in': valid_pages}}, {'$set': {'has_gen_chars': True}})
        log = dict(inserted_char=[c['name'] for c in un_existed], updated_char=[c['name'] for c in existed],
                   deleted_char=[c['name'] for c in deleted], invalid_char=invalid_chars,
                   valid_pages=valid_pages, invalid_pages=invalid_pages,
                   create_time=datetime.now())
        CharHandler.add_op_log(db, 'gen_chars', 'finished', log, username)


if __name__ == '__main__':
    import fire

    fire.Fire(gen_chars)
