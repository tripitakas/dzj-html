#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import json
import shutil
import pymongo
from glob2 import glob
from bson import json_util
from tornado.util import PY3
from datetime import datetime
from os import path, makedirs, walk
from pymongo.errors import PyMongoError

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.tool.diff import Diff
from controller.helper import prop, align_code
from controller.page.base import PageHandler as Ph


def case1(db):
    name = 'YB_25_692'
    page = db.page.find_one({'name': name})
    Ph.apply_ocr_col(page)
    db.page.update_one({'name': name}, {'$set': {'chars': page['chars']}})


def case2(db):
    ocr_txt = '四分律刪補隨機羯磨卷上第六張訓舊'
    ocr_col = '豸律刪補隨機羯磨卷上第六張訓羅引'
    segments = Diff.diff(ocr_txt, ocr_col, check_variant=False)[0]
    for s in segments:
        print(s)


def main(db_name='tripitaka', uri='localhost', func='case2', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
