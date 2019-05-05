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


def i18n_trans(key):
    maps = {
        'name': '姓名',
        'phone': '手机',
        'email': '邮箱',
        'password': '密码',
        'old_password': '原始密码',
        'gender': '性别',
    }
    return maps[key] if key in maps else key


def allowed_keys(**kw):
    """申明需要哪些数据属性"""
    pass


def not_empty(**kw):
    code, message = e.not_allowed_empty
    errs = {k: (code, message % i18n_trans(k)) for k, v in kw.items() if not v}
    return errs or None


def not_both_empty(**kw):
    assert len(kw) == 2
    k1, k2 = kw.keys()
    v1, v2 = kw.values()
    code, message = e.not_allowed_both_empty
    err = code, message % (i18n_trans(k1), i18n_trans(k2))
    if not v1 and not v2:
        return {k1: err, k2: err}


def not_equal(**kw):
    assert len(kw) == 2
    k1, k2 = kw.keys()
    v1, v2 = kw.values()
    code, message = e.not_allow_equal
    err = code, message % (i18n_trans(k1), i18n_trans(k2))
    if v1 == v2:
        return {k1: err, k2: err}


def equal(**kw):
    assert len(kw) == 2
    k1, k2 = kw.keys()
    v1, v2 = kw.values()
    code, message = e.not_equal
    err = code, message % (i18n_trans(k1), i18n_trans(k2))
    if v1 != v2:
        return {k1: err, k2: err}


def is_name(name='', **kw):
    """ 检查是否为姓名。参数可以为字符串或者字典。"""
    if kw:
        assert len(kw) == 1
        k, v = list(kw.items())[0]
    else:
        k, v = '', name
    regex = r'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'
    if v and not re.match(regex, v):
        return {k: e.invalid_name}


def is_phone(phone='', **kw):
    """ 检查是否为手机。参数可以为字符串或者字典。"""
    if kw:
        assert len(kw) == 1
        k, v = list(kw.items())[0]
    else:
        k, v = '', phone
    regex = r'^1[34578]\d{9}$'
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_phone}


def is_email(email='', **kw):
    """ 检查是否为邮箱。参数可以为字符串或者字典。"""
    if kw:
        assert len(kw) == 1
        k, v = list(kw.items())[0]
    else:
        k, v = '', email
    regex = r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$'
    if v and not re.match(regex, v):
        return {k: e.invalid_email}


def is_phone_or_email(phone_or_email='', **kw):
    """ 检查是否为邮箱。参数可以为字符串或者字典。"""
    if kw:
        assert len(kw) == 1
        k, v = list(kw.items())[0]
    else:
        k, v = 'phone_or_email', phone_or_email
    email_regex = r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$'
    phone_regex = r'^1[34578]\d{9}$'
    if v and not re.match(email_regex, phone_or_email) and not re.match(phone_regex, phone_or_email):
        return {k: e.invalid_phone_or_email}


def is_password(password='', **kw):
    """ 检查是否为密码。参数可以为字符串或者字典。"""
    if kw:
        assert len(kw) == 1
        k, v = list(kw.items())[0]
    else:
        k, v = '', password
    regex = r'^(?![0-9]+$)(?![a-zA-Z]+$)[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$'
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_password}


def between(min, max, **kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    code, message = e.invalid_range
    err = code, message % (i18n_trans(k), min, max)
    if v < min or v > max:
        return {k: err}


def not_existed(collection=None, exclude_id=None, **kw):
    """
    校验数据库中是否已存在kw中对应的记录
    :param collection: mongdb的collection
    :param exclude_id: 校验时，排除某个id对应的记录
    """
    errs = {}
    code, message = e.record_existed
    if collection:
        for k, v in kw.items():
            condition = {k: v}
            if exclude_id:
                condition['_id'] = {'$ne': exclude_id}
            if v and collection.find_one(condition):
                errs[k] = code, message % i18n_trans(k)
    return errs or None


def is_unique(collection=None, **kw):
    """校验数据库中是否唯一"""
    errs = {}
    code, message = e.record_existed
    if collection:
        for k, v in kw.items():
            if v and collection.find({k: v}).count() > 1:
                errs[k] = code, message % i18n_trans(k)
    return errs or None


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
        (between, 'age', 10, 100),
    ]

    errs = validate(data, rules)
    for k, v in errs.items():
        print(k, v)
