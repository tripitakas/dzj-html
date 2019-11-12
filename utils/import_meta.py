#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import pymongo
from glob2 import glob
import os.path as path

sys.path.append(path.dirname(path.dirname(__file__)))
from controller.data.data import Tripitaka, Volume, Reel, Sutra

META_DIR = path.join(path.dirname(__file__), '..', 'meta', 'meta')


def import_meta(db, collection, csv_file):
    sys.stdout.write('importing %s: %s...\n' % (collection, path.basename(csv_file)))
    with open(csv_file) as fn:
        collection_class = eval(collection.capitalize())
        collection_class.save_many(db, collection, file_stream=fn)


def main(db_name='tripitaka', uri='localhost', collections='tripitaka,sutra,reel,volume',
         which='', reset=False):
    """ 导入基础数据
    :param collections, 导入哪些数据集合，多个时用逗号分隔，如'tripitaka,sutra,reel,volume'
    :param which, 导入哪部藏经，比如GL（高丽藏）。默认为空，导入所有藏经。
    :param reset, 是否清空collections
    """
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    for collection in collections.split(','):
        if reset:
            db[collection].drop()

        if which:  # 导入某部藏经
            filename = path.join(META_DIR, '%s-%s.csv' % (collection, which))
            import_meta(db, collection, filename)
        else:  # 导入所有藏经
            for filename in glob(path.join(META_DIR, '%s*.csv' % collection)):
                import_meta(db, collection, filename)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished!')
