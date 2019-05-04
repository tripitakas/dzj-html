#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据校验类
@time: 2019/4/29
"""

import re
import controller.errors as e


def validate(data, rules):
    """
    数据校验主控函数
    :param data:  待校验的数据，一般是指从页面POST的dict类型的数据
    :param rules: 校验规则列表，每个rule是一个(func, para1, para2, ...)元组，其中，func是校验工具函数。关于para1、para2等参数：
                  1. 如果是字符串格式，则表示data的属性，将data[para1]数据作为参数传递给func函数
                  2. 如果不是字符串格式，则直接作为参数传递给func函数
    :return: 如果校验有误，则返回校验错误，格式为{key: (error_code, message)}，其中，key为data的属性。无误，则无返回值。
    """
    errs = {}
    for rule in rules:
        func = rule[0]
        kw = {para: data.get(para) for para in rule[1:] if isinstance(para, str)}
        args = [para for para in rule[1:] if not isinstance(para, str)]
        ret = func(*args, **kw)
        if ret:
            errs.update(ret)
    return errs or None


def allowed_keys(**kw):
    """申明需要哪些数据属性"""
    pass


def not_empty(**kw):
    errs = {k: e.not_allowed_empty for k, v in kw.items() if not v}
    return errs or None


def not_both_empty(**kw):
    assert len(kw) == 2
    k1, k2 = kw.keys()
    v1, v2 = kw.values()
    code, message = e.not_allowed_both_empty
    err = code, message % (k1, k2)
    if not v1 and not v2:
        return {k1: err, k2: err}


def is_name(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'
    if v and not re.match(regex, v):
        return {k: e.invalid_name}


def is_phone(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^1[34578]\d{9}$'
    if v and not re.match(regex, v):
        return {k: e.invalid_phone}


def is_email(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$'
    if v and not re.match(regex, v):
        return {k: e.invalid_email}


def is_password(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^(?![0-9]+$)(?![a-zA-Z]+$)[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$'
    if v and not re.match(regex, v):
        return {k: e.invalid_password}


def between(min, max, **kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    code, message = e.invalid_range
    err = code, message % (min, max)
    if v < min or v > max:
        return {k: err}


if __name__ == '__main__':
    # TODO: 这段测试可移到单元测试中
    data = {'name': '1234567890', 'phone': '', 'email': '', 'password': '', 'age': 8}
    rules = [
        (allowed_keys, 'name', 'phone', 'email', 'password'),
        (not_empty, 'name', 'password'),
        (not_both_empty, 'phone', 'email'),
        (is_name, 'name'),
        (is_phone, 'phone'),
        (is_email, 'email'),
        (is_password, 'password'),
        (between, 'age', 10, 100)
    ]

    errs = validate(data, rules)
    for k, v in errs.items():
        print(k, v)
