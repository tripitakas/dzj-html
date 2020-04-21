#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.page.tool.variant import variants


def add_variants(db_name='tripitaka', uri='localhost'):
    db = pymongo.MongoClient(uri)[db_name]
    variants2insert = []
    for v_str in variants:
        for item in v_str:
            variants2insert.append(dict(txt=item, normal_txt=v_str[0]))
    db.variant.insert_many(variants2insert, ordered=False)
    print('add %s variants' % len(variants2insert))


if __name__ == '__main__':
    import fire

    fire.Fire(add_variants)
