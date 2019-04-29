#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据校验类
@time: 2019/4/29
"""

import re
import logging
import inspect
from datetime import datetime, timedelta
from hashids import Hashids
from pyconvert.pyconv import convertJSON2OBJ



def validate(data, rules):
    """
    数据校验主控函数
    :param data: 待校验的数据，一般是指从页面POST的dict类型的数据
    :param rules: 校验规则列表，每一rule是一个(func, para1, para2, ...)元组，func是校验工具函数。关于para1、para2等参数：
                  1. 如果是字符串格式，则表示为data的属性，则将data[para1]数据作为参数传递给func函数
                  2. 如果不是字符串格式，则直接作为参数传递给func函数
    :return: 如果校验有误，则返回校验错误代码。无误，则无返回值。
    """
    for k, rule in rules.items():
        ret = rule(data.get(k))
        if ret.has_error:
            return ret


def is_name(name):
    pass


def between(age, min, max):
    pass