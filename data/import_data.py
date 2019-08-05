#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
from glob2 import glob
import os.path as path
import pymongo
from controller.app import Application as App
from datetime import datetime, timedelta

META_DIR = './meta'


def get_db():
    cfg = App.load_config()['database']
    login = '{0}:{1}@'.format(cfg.get('user'), cfg.get('password')) if cfg.get('user') else ''
    uri = 'mongodb://{0}{1}:{2}'.format(login, cfg.get('host'), cfg.get('port', 27017))
    conn = pymongo.MongoClient(
        uri, connectTimeoutMS=2000, serverSelectionTimeoutMS=2000, maxPoolSize=10, waitQueueTimeoutMS=5000
    )
    return conn[cfg.get('name')]


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def import_tripitaka():
    """ 导入tripitaka meta数据 """
    meta_csv = path.join(META_DIR, 'Tripitaka.csv')
    print('import tripitaka: %s...' % meta_csv)
    db = get_db()
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            db.tripitaka.insert_one(data)


def import_volume(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Volume-%s.csv' % tripitaka)
    print('import volume: %s...' % meta_csv)
    db = get_db()
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            db.volume.insert_one(data)


def import_sutra(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Sutra-%s.csv' % tripitaka)
    print('import sutra: %s...' % meta_csv)
    db = get_db()
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            db.sutra.insert_one(data)


def import_reel(tripitaka):
    """ 导入volume meta数据 """
    meta_csv = path.join(META_DIR, 'Reel-%s.csv' % tripitaka)
    print('import reel: %s...' % meta_csv)
    db = get_db()
    with open(meta_csv) as fn:
        rows = list(csv.reader(fn))
        heads = rows[0]
        for row in rows[1:]:
            data = {heads[i]: item for i, item in enumerate(row)}
            data.update({
                'create_time': get_date_time(),
                'updated_time': get_date_time(),
            })
            db.reel.insert_one(data)


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


def export_tripitaka():
    db = get_db()
    with open(path.join(META_DIR, 'Tripitaka.csv'), 'w', newline='') as fn:
        writer = csv.writer(fn)
        rows = list(db.tripitaka.find({}, {'_id': 0, 'create_time': 0, 'updated_time': 0}))
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            info = list(row.values())
            writer.writerow(info)


def export_volume(tripitaka):
    db = get_db()
    with open(path.join(META_DIR, 'Volume-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        rows = list(db.volume.find({'tripitaka_code': tripitaka}, {'_id': 0, 'create_time': 0, 'updated_time': 0}))
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            info = list(row.values())
            writer.writerow(info)


def export_sutra(tripitaka):
    db = get_db()
    with open(path.join(META_DIR, 'Sutra-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        rows = list(db.sutra.find(
            {'sutra_code': {'$regex': '%s.*' % tripitaka}}, {'_id': 0, 'create_time': 0, 'updated_time': 0}
        ))
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            info = list(row.values())
            writer.writerow(info)


def export_reel(tripitaka):
    db = get_db()
    with open(path.join(META_DIR, 'Reel-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        rows = list(db.reel.find(
            {'sutra_code': {'$regex': '%s.*' % tripitaka}}, {'_id': 0, 'create_time': 0, 'updated_time': 0}
        ))
        writer.writerow(list(rows[0].keys()))
        for row in rows:
            info = list(row.values())
            writer.writerow(info)


def export_meta():
    export_tripitaka()

    tripitakas = ['JX', 'FS', 'HW', 'QD', 'QS', 'SZ', 'YG', 'ZH', 'PL', 'QL', 'SX', 'YB', 'ZC']
    for tripitaka in tripitakas:
        export_volume(tripitaka)

    tripitakas = ['GL', 'HW', 'KB', 'LC', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        export_sutra(tripitaka)

    tripitakas = ['GL', 'HW', 'KB', 'LC', 'QD', 'QL', 'QS', 'SZ', 'YB', 'ZC', 'ZH']
    for tripitaka in tripitakas:
        export_reel(tripitaka)


def main(db_name='tripitaka', uri='localhost', reset=False):
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
