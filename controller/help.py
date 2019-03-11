#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 后端辅助类
@time: 2019/3/10
"""

import logging
import re
from datetime import datetime, timedelta

from hashids import Hashids
from pyconvert.pyconv import convertJSON2OBJ

from model.user import authority_map, ACCESS_ALL



def my_framer():
    old_framer = logging.currentframe
    f0 = f = old_framer()
    if f is not None:
        f = f.f_back
        while re.search(r'(web|base)\.py|logging', f.f_code.co_filename):
            f0 = f
            f = f.f_back
    return f0

def fetch_authority(user, record):
    """ 从记录中读取权限字段值 """
    authority = None
    if record:
        items = [authority_map[f] for f in list(authority_map.keys()) if record.get(f)]
        authority = ','.join(sorted(items, key=lambda a: ACCESS_ALL.index(a) if a in ACCESS_ALL else -1))
    if user:
        user.authority = authority or '普通用户'
    return authority


def convert_bson(r):
    if not r:
        return r
    for k, v in (r.items() if isinstance(r, dict) else enumerate(r)):
        if type(v) == datetime:
            r[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(v, dict):
            convert_bson(v)
    if 'update_time' not in r and 'create_time' in r:
        r['update_time'] = r['create_time']
    if '_id' in r:
        r['id'] = str(r.pop('_id'))
    return r


def convert2obj(cls, json_obj):
    """ 将JSON对象转换为指定模型类的对象 """
    if isinstance(json_obj, dict):
        for k, v in list(json_obj.items()):
            if v is None or v == str:
                json_obj.pop(k)
    obj = convertJSON2OBJ(cls, json_obj)
    fields = [f for f in cls.__dict__.keys() if f[0] != '_']
    for f in fields:
        if f not in obj.__dict__:
            obj.__dict__[f] = None
    return obj



def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def gen_id(value, salt='', rand=False, length=16):
    coder = Hashids(salt=salt and rand and salt + str(datetime.now().second) or salt, min_length=16)
    if isinstance(value, bytes):
        return coder.encode(*value)[:length]
    return coder.encode(*[ord(c) for c in list(value)])[:length]


def create_object(cls, value, salt='', rand=False, length=16):
    fields = [f for f in cls.__dict__.keys() if f[0] != '_']
    obj = cls()
    for f in fields:
        if f not in obj.__dict__:
            obj.__dict__[f] = None
    obj.id = gen_id(value, salt, rand=rand, length=length)
    return obj