#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import csv
import json
import pymongo
import os.path as path
from functools import cmp_to_key
from datetime import datetime, timedelta

META_DIR = './meta'
global_db = ''


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def import_tripitaka():
    """ 导入tripitaka meta数据 """
    meta_csv = path.join(META_DIR, 'Tripitaka.csv')
    print('import tripitaka: %s...' % meta_csv)
    global global_db
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            global_db.tripitaka.insert_one(data)


def get_code_value(code):
    slice = [c.zfill(4) for c in code.split('_') if re.sub('[a-zA-Z]', '', c)]
    value = ''.join(slice)
    if not re.match(r'^\d+$', value):
        print('error code ' + code)
    return int(value) if value else 0


def import_volume(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Volume-%s.csv' % tripitaka)
    print('import volume: %s...' % meta_csv)
    global global_db
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            content_pages = json.loads(data['content_pages'].replace("'", '"'))
            content_pages = [p for p in content_pages if '_f' not in p and '_b' not in p]
            content_pages.sort(key=cmp_to_key(lambda a, b: get_code_value(a) - get_code_value(b)))
            update = {
                'name': data['name'],
                'tripitaka_code': data['tripitaka_code'],
                'volume_num': data['volume_num'],
                'first_page': data['first_page'],
                'last_page': data['last_page'],
                'content_page_count': data['content_page_count'],
                'front_cover_count': data['front_cover_count'],
                'back_cover_count': data['back_cover_count'],
                'content_pages': content_pages,
                'remark': data['remark'],
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            }
            global_db.volume.insert_one(update)


def import_sutra(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Sutra-%s.csv' % tripitaka)
    print('import sutra: %s...' % meta_csv)
    global global_db
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            global_db.sutra.insert_one(data)


def import_reel(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Reel-%s.csv' % tripitaka)
    print('import reel: %s...' % meta_csv)
    global global_db
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            global_db.reel.insert_one(data)


def import_meta():
    import_tripitaka()

    tripitakas = ['JX', 'FS', 'HW', 'QD', 'QS', 'SZ', 'YG', 'ZH', 'PL', 'QL', 'SX', 'YB', 'ZC']
    for tripitaka in tripitakas:
        import_volume(tripitaka)

    tripitakas = ['GL', 'HW', 'KB', 'LC', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        import_sutra(tripitaka)

    tripitakas = ['GL', 'HW', 'KB', 'LC', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        import_reel(tripitaka)


def main(db_name='tripitaka', uri='localhost', reset=False):
    global global_db
    conn = pymongo.MongoClient(uri)
    global_db = conn[db_name]
    if reset:
        global_db.tripitaka.drop()
        global_db.sutra.drop()
        global_db.reel.drop()
        global_db.volume.drop()

    import_meta()


if __name__ == '__main__':
    import fire

    fire.Fire(main)
