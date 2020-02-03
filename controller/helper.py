#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 后端辅助类
@time: 2019/3/10
"""

import re
import random
import hashlib
import logging
import inspect
from hashids import Hashids
from urllib.parse import unquote
from datetime import datetime, timedelta, timezone

from tornado.util import PY3
from os import path
from yaml import load as load_yml, SafeLoader
import pymongo

BASE_DIR = path.dirname(path.dirname(__file__))


def load_config():
    param = dict(encoding='utf-8') if PY3 else {}
    cfg_base = path.join(BASE_DIR, '_app.yml')
    cfg_file = path.join(BASE_DIR, 'app.yml')
    config = {}

    with open(cfg_base, **param) as f:
        config_base = load_yml(f, Loader=SafeLoader)
    if path.exists(cfg_file):
        with open(cfg_file, **param) as f:
            config = load_yml(f, Loader=SafeLoader)
    else:
        with open(cfg_file, 'w') as f:
            f.write('todo:')
    for k, v in config_base.items():
        if k not in config:
            config[k] = v

    return config


def connect_db(cfg, db_name_ext=''):
    if cfg.get('user'):
        uri = 'mongodb://{0}:{1}@{2}:{3}/admin'.format(
            cfg.get('user'), cfg.get('password'), cfg.get('host'), cfg.get('port', 27017)
        )
    else:
        uri = 'mongodb://{0}:{1}/'.format(cfg.get('host') or '127.0.0.1', cfg.get('port', 27017))
    conn = pymongo.MongoClient(
        uri, connectTimeoutMS=2000, serverSelectionTimeoutMS=2000,
        maxPoolSize=10, waitQueueTimeoutMS=5000
    )
    return conn[cfg['name'] + db_name_ext], uri


def md5_encode(page_code, salt):
    md5 = hashlib.md5()
    md5.update((page_code + salt).encode('utf-8'))
    return md5.hexdigest()


def get_date_time(fmt=None, date_time=None, diff_seconds=None):
    time = date_time if date_time else datetime.now()
    if isinstance(time, str):
        try:
            time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return time
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)

    time_zone = timezone(timedelta(hours=8))
    return time.astimezone(time_zone).strftime(fmt or '%Y-%m-%d %H:%M:%S')


def gen_id(value, salt='', rand=False, length=16):
    coder = Hashids(salt=salt and rand and salt + str(datetime.now().second) or salt, min_length=16)
    if isinstance(value, bytes):
        return coder.encode(*value)[:length]
    return coder.encode(*[ord(c) for c in list(value or [])])[:length]


def cmp_page_code(a, b):
    """ 比较图片名称大小 """
    al, bl = a.split('_'), b.split('_')
    if len(al) != len(bl):
        return len(al) - len(bl)
    for i in range(len(al)):
        length = max(len(al[i]), len(bl[i]))
        ai, bi = al[i].zfill(length), bl[i].zfill(length)
        if ai != bi:
            return 1 if ai > bi else -1
    return 0


def random_code():
    code = ''
    for i in range(4):
        current = random.randrange(0, 4)
        if current != i:
            temp = chr(random.randint(65, 90))
        else:
            temp = random.randint(0, 9)
        code += str(temp)
    return code


def prop(obj, key, default=None):
    obj = obj or dict()
    for s in key.split('.'):
        obj = obj.get(s) if isinstance(obj, dict) else None
    return default if obj is None else obj


def get_url_param(key, url_query):
    regex = r'(^|\?|&)%s=(.*?)($|&)' % key
    r = re.search(regex, url_query, re.I)
    return unquote(r.group(2)) if r else ''


def my_framer():
    """ 出错输出日志时原本显示的是底层代码文件，此类沿调用堆栈往上显示更具体的调用者 """
    f0 = f = old_framer()
    if f is not None:
        until = [s[1] for s in inspect.stack() if re.search(r'controller/(view|api)', s[1])]
        if until:
            while f.f_code.co_filename != until[0]:
                f0 = f
                f = f.f_back
            return f0
        f = f.f_back
        while re.search(r'web\.py|logging', f.f_code.co_filename):
            f0 = f
            f = f.f_back
    return f0


old_framer = logging.currentframe
logging.currentframe = my_framer
