#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import csv
import sys
import json
import pymongo
import os.path as path
from functools import cmp_to_key
from datetime import datetime, timedelta
from glob2 import glob

META_DIR = path.join(path.dirname(__file__), 'meta')
db = ''


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def import_tripitaka():
    """ 导入tripitaka meta数据 """
    meta_csv = path.join(META_DIR, 'Tripitaka.csv')
    sys.stdout.write('import tripitaka: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 50 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            if not db.tripitaka.find_one({heads[0]: row[0]}):
                db.tripitaka.insert_one(data)
                added += 1
    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def get_code_value(code):
    slice = [c.zfill(4) for c in code.split('_') if re.sub('[a-zA-Z]', '', c)]
    value = ''.join(slice)
    if not re.match(r'^\d+$', value):
        print('error code ' + code)
    return int(value) if value else 0


def import_volume(tripitaka, meta_csv):
    """ 导入volume meta数据 """
    sys.stdout.write('import volume: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 50 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
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
            if not db.volume.find_one({heads[0]: row[0]}):
                db.volume.insert_one(update)
                added += 1
    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def import_sutra(tripitaka, meta_csv):
    """ 导入volume meta数据 """
    sys.stdout.write('import sutra: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 50 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            if not db.sutra.find_one({heads[0]: row[0]}):
                db.sutra.insert_one(data)
                added += 1
    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def import_reel(tripitaka, meta_csv):
    """ 导入volume meta数据 """
    sys.stdout.write('import reel: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 50 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            if not db.reel.find_one({heads[0]: row[0]}):
                db.reel.insert_one(data)
                added += 1
    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def import_meta():
    import_tripitaka()

    for filename, code in glob(path.join(META_DIR, 'Volume-*.csv'), True):
        import_volume(code[0], filename)
    for filename, code in glob(path.join(META_DIR, 'Sutra-*.csv'), True):
        import_sutra(code[0], filename)
    for filename, code in glob(path.join(META_DIR, 'Reel-*.csv'), True):
        import_reel(code[0], filename)


def main(db_name='tripitaka', uri='localhost', reset=False):
    global db
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    if reset:
        db.tripitaka.drop()
        db.sutra.drop()
        db.reel.drop()
        db.volume.drop()

    import_meta()


if __name__ == '__main__':
    import fire

    fire.Fire(main)
