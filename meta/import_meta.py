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
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'created_time': get_date_time(),
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


def import_volume(tripitaka):
    """ 导入volume meta数据，字段依次为：
        'volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_pages', 'front_cover_pages',
        'back_cover_pages', 'remark', 'created_time', 'updated_time'
    """
    meta_csv = path.join(META_DIR, 'Volume-%s.csv' % tripitaka)
    sys.stdout.write('import volume: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            data = {heads[i]: item for i, item in enumerate(row)}
            content_pages = json.loads(data['content_pages'].replace("'", '"'))
            content_pages.sort(key=cmp_to_key(lambda a, b: get_code_value(a) - get_code_value(b)))
            front_cover_pages = json.loads(data['front_cover_pages'].replace("'", '"')) if data.get(
                'front_cover_pages') else None
            back_cover_pages = json.loads(data['back_cover_pages'].replace("'", '"')) if data.get(
                'back_cover_pages') else None
            update = {
                'volume_code': data['volume_code'],
                'tripitaka_code': data['tripitaka_code'],
                'envelop_no': int(data.get('envelop_no')) if data.get('envelop_no') else None,
                'volume_no': int(data.get('volume_no')) if data.get('volume_no') else None,
                'content_page_count': len(content_pages),
                'content_pages': content_pages,
                'front_cover_pages': front_cover_pages,
                'back_cover_pages': back_cover_pages,
                'remark': data['remark'],
                'created_time': get_date_time(),
                'updated_time': get_date_time(),
            }
            if not db.volume.find_one({'volume_code': data['volume_code']}):
                db.volume.insert_one(update)
                added += 1
    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def import_sutra(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Sutra-%s.csv' % tripitaka)
    sys.stdout.write('import sutra: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            d = {heads[i]: item for i, item in enumerate(row)}
            update = {
                'unified_sutra_code': d.get('unified_sutra_code'),
                'sutra_code': d.get('sutra_code'),
                'sutra_name': d.get('sutra_name'),
                'due_reel_count': int(d.get('due_reel_count')) if d.get('due_reel_count') else None,
                'existed_reel_count': int(d.get('existed_reel_count')) if d.get('existed_reel_count') else None,
                'author': d.get('author'),
                'trans_time': d.get('trans_time'),
                'start_volume': d.get('start_volume'),
                'start_page': int(d.get('start_page')) if d.get('start_page') else None,
                'end_volume': d.get('end_volume'),
                'end_page': int(d.get('end_page')) if d.get('end_page') else None,
                'remark': d.get('remark'),
                'created_time': get_date_time(),
                'updated_time': get_date_time(),
            }
            if not db.sutra.find_one({'sutra_code': update['sutra_code']}):
                db.sutra.insert_one(update)
                added += 1

    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def import_reel(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Reel-%s.csv' % tripitaka)
    sys.stdout.write('import reel: %s ' % path.basename(meta_csv))
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        added = 0
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            data = {heads[i]: item for i, item in enumerate(row)}
            update = {
                'unified_sutra_code': data.get('unified_sutra_code'),
                'sutra_code': data.get('sutra_code'),
                'sutra_name': data.get('sutra_name'),
                'reel_no': int(data.get('reel_no')) if data.get('reel_no') else None,
                'start_volume': data.get('start_volume'),
                'start_page': int(data.get('start_page')) if data.get('start_page') else None,
                'end_volume': data.get('end_volume'),
                'end_page': int(data.get('end_page')) if data.get('end_page') else None,
                'remark': data.get('remark'),
                'created_time': get_date_time(),
                'updated_time': get_date_time(),
            }
            if not db.reel.find_one({'sutra_code': update['sutra_code'], 'reel_no': update['reel_no']}):
                db.reel.insert_one(update)
                added += 1
    sys.stdout.write(' %d added in %d items\n' % (added, len(rows) - 1))


def import_meta():
    import_tripitaka()

    for filename, code in glob(path.join(META_DIR, 'Volume-*.csv'), True):
        import_volume(code[0])

    for filename, code in glob(path.join(META_DIR, 'Sutra-*.csv'), True):
        import_sutra(code[0])

    for filename, code in glob(path.join(META_DIR, 'Reel-*.csv'), True):
        import_reel(code[0])


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
    main()
    print('finished!')
