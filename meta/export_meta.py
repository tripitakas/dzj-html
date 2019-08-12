#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import pymongo
import os.path as path
from datetime import datetime, timedelta

META_DIR = path.join(path.dirname(__file__), 'meta')
db = ''


def export_tripitaka():
    with open(path.join(META_DIR, 'Tripitaka.csv'), 'w', newline='') as fn:
        writer = csv.writer(fn)
        rows = list(db.tripitaka.find({}, {'_id': 0, 'create_time': 0, 'updated_time': 0}))
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            info = list(row.values())
            writer.writerow(info)


def export_volume(tripitaka):
    with open(path.join(META_DIR, 'Volume-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        fields = ['volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_page_count', 'content_pages',
                  'front_cover_pages', 'back_cover_pages', 'remark']
        writer.writerow(fields)
        rows = list(db.volume.find({'tripitaka_code': tripitaka}).sort([('envelop_no', 1), ('volume_no', 1)]))
        for row in rows:
            info = [row.get(f) for f in fields]
            writer.writerow(info)


def export_sutra(tripitaka):
    with open(path.join(META_DIR, 'Sutra-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        fields = ['unified_sutra_code', 'sutra_code', 'sutra_name', 'due_reel_count', 'existed_reel_count',
                  'author', 'trans_time', 'start_volume', 'start_page', 'end_volume', 'end_page', 'remark']
        writer.writerow(fields)
        rows = list(db.sutra.find({'sutra_code': {'$regex': '^%s.*' % tripitaka}}))
        for row in rows:
            info = [row.get(f) for f in fields]
            writer.writerow(info)


def export_reel(tripitaka):
    with open(path.join(META_DIR, 'Reel-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        fields = ['unified_sutra_code', 'sutra_code', 'sutra_name', 'reel_no',
                  'start_volume', 'start_page', 'end_volume', 'end_page', 'remark']
        writer.writerow(fields)
        rows = list(db.reel.find({'sutra_code': {'$regex': '^%s.*' % tripitaka}}))
        for row in rows:
            info = [row.get(f) for f in fields]
            writer.writerow(info)


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def export_meta():
    export_tripitaka()

    tripitakas = ['GL', 'LC', 'JX', 'JS', 'FS', 'HW', 'QD', 'QS', 'SZ', 'YG', 'ZH', 'PL', 'QL', 'SX', 'YB', 'ZC']
    for tripitaka in tripitakas:
        export_volume(tripitaka)

    tripitakas = ['GL', 'HW', 'KB', 'LC', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        export_sutra(tripitaka)

    tripitakas = ['GL', 'HW', 'KB', 'LC', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        export_reel(tripitaka)


def main(db_name='tripitaka', uri='localhost'):
    global db
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    export_meta()


if __name__ == '__main__':
    import fire

    fire.Fire(main)
