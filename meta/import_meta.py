#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import csv
import sys
import json
import pymongo
from glob2 import glob
import os.path as path
from functools import cmp_to_key
import controller.errors as errors
from datetime import datetime, timedelta

META_DIR = path.join(path.dirname(__file__), 'meta')


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def get_code_value(code):
    slice = [c.zfill(4) for c in code.split('_') if re.sub('[a-zA-Z]', '', c)]
    value = ''.join(slice)
    if not re.match(r'^\d+$', value):
        print('error code ' + code)
    return int(value) if value else 0


def import_tripitaka(db, csv_file_or_list, reset=False):
    """ 导入tripitaka数据 """

    def gen_item():
        return {
            'tripitaka_code': d.get('tripitaka_code') or '',
            'name': d.get('name') or '',
            'short_name': d.get('short_name') or '',
            'store_pattern': d.get('store_pattern') or '',
            'img_available': d.get('img_available') or '',
            'img_prefix': d.get('img_prefix') or '',
            'img_suffix': d.get('img_suffix') or '',
            'created_time': get_date_time(),
            'updated_time': get_date_time(),
        }

    if isinstance(csv_file_or_list, str) and path.exists(csv_file_or_list):
        sys.stdout.write('importing tripitaka: %s...' % path.basename(csv_file_or_list))
        with open(csv_file_or_list) as fn:
            rows = list(csv.reader(fn))
    elif isinstance(csv_file_or_list, list):
        rows = csv_file_or_list
    else:
        return False, '不是csv文件或数组'

    heads = rows[0]
    fields = ['tripitaka_code', 'name', 'short_name', 'store_pattern', 'img_available', 'img_prefix', 'img_suffix']
    need_head = [r for r in fields if r not in heads]
    if need_head:
        return errors.tripitaka_csv_head_error[0], '文件缺字段：%s' % ','.join(need_head)

    if reset:
        items = []
        for r, row in enumerate(rows[1:]):
            d = {heads[i]: item for i, item in enumerate(row)}
            items.append(gen_item())
        db.tripitaka.insert_many(items)
    else:
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            db.tripitaka.find_one_and_update(
                {'tripitaka_code': update.get('tripitaka_code')}, {'$set': update}, upsert=True
            )

    msg = '%d added or updated in %d items.\n' % (len(rows) - 1, len(rows) - 1)
    sys.stdout.write(msg)
    return 200, msg


def import_volume(db, csv_file_or_list, reset=False):
    """ 导入volume数据 """

    def gen_item():
        try:
            content_pages = json.loads(d['content_pages'].replace("'", '"'))
            content_pages.sort(key=cmp_to_key(lambda a, b: get_code_value(a) - get_code_value(b)))
            front_cover_pages = json.loads(d['front_cover_pages'].replace("'", '"')) if d.get(
                'front_cover_pages') else None
            back_cover_pages = json.loads(d['back_cover_pages'].replace("'", '"')) if d.get(
                'back_cover_pages') else None
            item = {
                'volume_code': d.get('volume_code') or '',
                'tripitaka_code': d.get('tripitaka_code') or '',
                'envelop_no': int(d.get('envelop_no')) if d.get('envelop_no') else None,
                'volume_no': int(d.get('volume_no')) if d.get('volume_no') else None,
                'content_page_count': len(content_pages),
                'content_pages': content_pages,
                'front_cover_pages': front_cover_pages,
                'back_cover_pages': back_cover_pages,
                'remark': d.get('remark') or '',
                'created_time': get_date_time(),
                'updated_time': get_date_time(),
            }
            return item
        except ValueError as e:
            sys.stdout.write('%s value error: %s' % (d.get('volume_code'), e))
            return False

    if isinstance(csv_file_or_list, str) and path.exists(csv_file_or_list):
        sys.stdout.write('importing volume: %s...' % path.basename(csv_file_or_list))
        with open(csv_file_or_list) as fn:
            rows = list(csv.reader(fn))
    elif isinstance(csv_file_or_list, list):
        rows = csv_file_or_list
    else:
        return False, '不是csv文件或数组'

    heads = rows[0]
    fields = ['volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_page_count', 'content_pages',
              'front_cover_pages', 'back_cover_pages', 'remark']
    need_head = [r for r in fields if r not in heads]
    if need_head:
        return errors.tripitaka_csv_head_error[0], '文件缺字段：%s' % ','.join(need_head)

    add_or_update, err = 0, []
    if reset:
        items = []
        for r, row in enumerate(rows[1:]):
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            if update:
                items.append(update)
                add_or_update += 1
            else:
                err.append(d.get('volume_code'))
        db.volume.insert_many(items)
    else:
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            if update:
                db.volume.find_one_and_update(
                    {'volume_code': update.get('volume_code')}, {'$set': update}, upsert=True
                )
                add_or_update += 1
            else:
                err.append(d.get('volume_code'))

    msg = '%d items, %d added or updated, %d errors: %s.\n' % (len(rows) - 1, add_or_update, len(err), ','.join(err))
    sys.stdout.write(msg)
    return 200, msg


def import_sutra(db, csv_file_or_list, reset=False):
    """ 导入sutra数据 """

    def gen_item():
        try:
            return {
                'unified_sutra_code': d.get('unified_sutra_code') or '',
                'sutra_code': d.get('sutra_code') or '',
                'sutra_name': d.get('sutra_name') or '',
                'due_reel_count': int(d.get('due_reel_count')) if d.get('due_reel_count') else None,
                'existed_reel_count': int(d.get('existed_reel_count')) if d.get('existed_reel_count') else None,
                'author': d.get('author') or '',
                'trans_time': d.get('trans_time') or '',
                'start_volume': d.get('start_volume') or '',
                'start_page': int(d.get('start_page')) if d.get('start_page') else None,
                'end_volume': d.get('end_volume') or '',
                'end_page': int(d.get('end_page')) if d.get('end_page') else None,
                'remark': d.get('remark') or '',
                'created_time': get_date_time(),
                'updated_time': get_date_time(),
            }
        except ValueError as e:
            sys.stdout.write('%s value error: %s' % (d.get('sutra_code'), e))
            return False

    if isinstance(csv_file_or_list, str) and path.exists(csv_file_or_list):
        sys.stdout.write('importing sutra: %s...' % path.basename(csv_file_or_list))
        with open(csv_file_or_list) as fn:
            rows = list(csv.reader(fn))
    elif isinstance(csv_file_or_list, list):
        rows = csv_file_or_list
    else:
        return False, '不是csv文件或数组'

    heads = rows[0]
    fields = ['unified_sutra_code', 'sutra_code', 'sutra_name', 'due_reel_count', 'existed_reel_count', 'author',
              'trans_time', 'start_volume', 'start_page', 'end_volume', 'end_page', 'remark']
    need_head = [r for r in fields if r not in heads]
    if need_head:
        return errors.tripitaka_csv_head_error[0], '文件缺字段：%s' % ','.join(need_head)

    add_or_update, err = 0, []
    if reset:
        items = []
        for r, row in enumerate(rows[1:]):
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            if update:
                items.append(update)
                add_or_update += 1
            else:
                err.append(d.get('sutra_code'))
        db.sutra.insert_many(items)
    else:
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            if update:
                db.sutra.find_one_and_update(
                    {'sutra_code': update.get('sutra_code')}, {'$set': update}, upsert=True
                )
                add_or_update += 1
            else:
                err.append(d.get('sutra_code'))

    msg = '%d items, %d added or updated, %d errors: %s.\n' % (len(rows) - 1, add_or_update, len(err), ','.join(err))
    sys.stdout.write(msg)
    return 200, msg


def import_reel(db, csv_file_or_list, reset=False):
    """ 导入reel数据 """

    def gen_item():
        try:
            return {
                'unified_sutra_code': d.get('unified_sutra_code') or '',
                'sutra_code': d.get('sutra_code') or '',
                'sutra_name': d.get('sutra_name') or '',
                'reel_no': int(d.get('reel_no')) if d.get('reel_no') else None,
                'start_volume': d.get('start_volume') or '',
                'start_page': int(d.get('start_page')) if d.get('start_page') else None,
                'end_volume': d.get('end_volume') or '',
                'end_page': int(d.get('end_page')) if d.get('end_page') else None,
                'remark': d.get('remark') or '',
                'created_time': get_date_time(),
                'updated_time': get_date_time(),
            }
        except ValueError as e:
            sys.stdout.write('%s_%s value error: %s' % (d.get('sutra_code'), d.get('reel_no'), e))
            return False

    if isinstance(csv_file_or_list, str) and path.exists(csv_file_or_list):
        sys.stdout.write('importing reel: %s...' % path.basename(csv_file_or_list))
        with open(csv_file_or_list) as fn:
            rows = list(csv.reader(fn))
    elif isinstance(csv_file_or_list, list):
        rows = csv_file_or_list
    else:
        return False, '不是csv文件或数组'

    heads = rows[0]
    fields = ['unified_sutra_code', 'sutra_code', 'sutra_name', 'reel_no', 'start_volume', 'start_page',
              'end_volume', 'end_page', 'remark']
    need_head = [r for r in fields if r not in heads]
    if need_head:
        return errors.tripitaka_csv_head_error[0], '文件缺字段：%s' % ','.join(need_head)

    add_or_update, err = 0, []
    if reset:
        items = []
        for r, row in enumerate(rows[1:]):
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            if update:
                items.append(update)
                add_or_update += 1
            else:
                err.append('%s_%s' % (d.get('sutra_code'), d.get('reel_no')))
        db.reel.insert_many(items)
    else:
        for r, row in enumerate(rows[1:]):
            if r % 100 == 0:
                sys.stdout.write('.')
                sys.stdout.flush()
            d = {heads[i]: item for i, item in enumerate(row)}
            update = gen_item()
            if update:
                db.reel.find_one_and_update(
                    {'sutra_code': update.get('sutra_code'), 'reel_no': update.get('reel_no')}, {'$set': update},
                    upsert=True
                )
                add_or_update += 1
            else:
                err.append('%s_%s' % (d.get('sutra_code'), d.get('reel_no')))

    msg = '%d items, %d added or updated, %d errors: %s.\n' % (len(rows) - 1, add_or_update, len(err), ','.join(err))
    sys.stdout.write(msg)
    return 200, msg


def main(db_name='tripitaka_test', uri='localhost', reset=True):
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    if reset:
        db.tripitaka.drop()
        db.sutra.drop()
        db.reel.drop()
        db.volume.drop()

    if path.exists(path.join(META_DIR, 'Tripitaka.csv')):
        import_tripitaka(db, path.join(META_DIR, 'Tripitaka.csv'), reset)

    for filename in glob(path.join(META_DIR, 'Volume-*.csv')):
        import_volume(db, filename, reset)

    for filename in glob(path.join(META_DIR, 'Sutra-*.csv')):
        import_sutra(db, filename, reset)

    for filename in glob(path.join(META_DIR, 'Reel-*.csv')):
        import_reel(db, filename, reset)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished!')
