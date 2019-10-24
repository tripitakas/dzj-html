#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import csv
import pymongo
import os.path as path

sys.path.append(path.dirname(path.dirname(__file__)))
from controller.data.data import Tripitaka, Volume, Reel, Sutra

META_DIR = path.join(path.dirname(__file__), '..', 'meta', 'meta')
db = ''


def export_tripitaka():
    filename = path.join(META_DIR, 'Tripitaka.csv')
    sys.stdout.write('exporting tripitaka: %s...' % path.basename(filename))
    with open(filename, 'w', newline='') as fn:
        writer = csv.writer(fn)
        heads = [f[1] for f in Tripitaka.fields]
        writer.writerow(heads)
        rows = list(db.tripitaka.find())
        for row in rows:
            info = [row.get(f[0]) for f in Tripitaka.fields]
            writer.writerow(info)
        sys.stdout.write('%s records exported\n' % len(rows))


def export_volume(tripitaka):
    filename = path.join(META_DIR, 'Volume-%s.csv' % tripitaka)
    sys.stdout.write('exporting tripitaka: %s...' % path.basename(filename))
    with open(filename, 'w', newline='') as fn:
        writer = csv.writer(fn)
        heads = [f[1] for f in Volume.fields]
        writer.writerow(heads)
        rows = list(db.volume.find({'tripitaka_code': tripitaka}).sort([('envelop_no', 1), ('volume_no', 1)]))
        for row in rows:
            info = [row.get(f[0]) for f in Volume.fields]
            writer.writerow(info)
        sys.stdout.write('%s records exported\n' % len(rows))


def export_sutra(tripitaka):
    filename = path.join(META_DIR, 'Sutra-%s.csv' % tripitaka)
    sys.stdout.write('exporting tripitaka: %s...' % path.basename(filename))
    with open(filename, 'w', newline='') as fn:
        writer = csv.writer(fn)
        heads = [f[1] for f in Sutra.fields]
        writer.writerow(heads)
        rows = list(db.sutra.find({'sutra_code': {'$regex': '^%s.*' % tripitaka}}))
        for row in rows:
            info = [row.get(f[0]) for f in Sutra.fields]
            writer.writerow(info)
        sys.stdout.write('%s records exported\n' % len(rows))


def export_reel(tripitaka):
    filename = path.join(META_DIR, 'Reel-%s.csv' % tripitaka)
    sys.stdout.write('exporting tripitaka: %s...' % path.basename(filename))
    with open(filename, 'w', newline='') as fn:
        writer = csv.writer(fn)
        heads = [f[1] for f in Reel.fields]
        writer.writerow(heads)
        rows = list(db.reel.find({'sutra_code': {'$regex': '^%s.*' % tripitaka}}))
        for row in rows:
            info = [row.get(f[0]) for f in Reel.fields]
            writer.writerow(info)
        sys.stdout.write('%s records exported\n' % len(rows))


def main(db_name='tripitaka_test', uri='localhost'):
    global db
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]

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


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished!')
