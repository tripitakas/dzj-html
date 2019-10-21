#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pymongo
from glob2 import glob
import os.path as path
sys.path.append(path.dirname(path.dirname(__file__)))

from controller.data.reel import Reel
from controller.data.sutra import Sutra
from controller.data.volume import Volume
from controller.data.tripitaka import Tripitaka

META_DIR = path.join(path.dirname(__file__), '..', 'meta', 'meta')


def import_tripitaka(db, csv_file, reset=False):
    """ 导入tripitaka数据 """
    sys.stdout.write('importing tripitaka: %s...\n' % path.basename(csv_file))
    with open(csv_file) as fn:
        r = Tripitaka.save_many(db, file_stream=fn, check_existed=reset)
        if r.get('status') == 'success':
            sys.stdout.write('import success: %s\n' % r.get('message'))
        else:
            sys.stdout.write('import failed: %s\n' % r.get('message'))


def import_volume(db, csv_file, reset=False):
    """ 导入volume数据 """
    sys.stdout.write('importing volume: %s...\n' % path.basename(csv_file))
    with open(csv_file) as fn:
        r = Volume.save_many(db, file_stream=fn, check_existed=reset)
        if r.get('status') == 'success':
            sys.stdout.write('import success: %s\n' % r.get('message'))
        else:
            sys.stdout.write('import failed: %s\n' % r.get('message'))


def import_sutra(db, csv_file, reset=False):
    """ 导入sutra数据 """
    sys.stdout.write('importing sutra: %s...\n' % path.basename(csv_file))
    with open(csv_file) as fn:
        r = Sutra.save_many(db, file_stream=fn, check_existed=reset)
        if r.get('status') == 'success':
            sys.stdout.write('import success: %s\n' % r.get('message'))
        else:
            sys.stdout.write('import failed: %s\n' % r.get('message'))


def import_reel(db, csv_file, reset=False):
    """ 导入reel数据 """
    sys.stdout.write('importing reel: %s...\n' % path.basename(csv_file))
    with open(csv_file) as fn:
        r = Reel.save_many(db, file_stream=fn, check_existed=not reset)
        if r.get('status') == 'success':
            sys.stdout.write('import success: %s\n' % r.get('message'))
        else:
            sys.stdout.write('import failed: %s\n' % r.get('message'))


def main(db_name='tripitaka', uri='localhost', reset=True):
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
