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
from datetime import datetime, timedelta, timezone



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


def is_box_changed(page_a, page_b, ignore_none=True):
    """检查两个页面的切分信息是否发生了修改"""
    for field in ['blocks', 'columns', 'chars']:
        a, b = page_a.get(field), page_b.get(field)
        if ignore_none and (not a or not b):
            continue
        if len(a) != len(b):
            return field + '.len'
        for i in range(len(a)):
            for j in ['x', 'y', 'w', 'h']:
                if abs(a[i][j] - b[i][j]) > 0.1 and (field != 'blocks' or len(a) > 1):
                    return '%s[%d] %s %f != %f' % (field, i, j, a[i][j], b[i][j])
    return None


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
    for s in key.split('.'):
        obj = obj.get(s) if isinstance(obj, dict) else None
    return default if obj is None else obj


old_framer = logging.currentframe
logging.currentframe = my_framer
