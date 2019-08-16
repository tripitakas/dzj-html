#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据校验类
@time: 2019/4/29
"""

import re
import controller.errors as e
from datetime import datetime, timedelta


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
    data['self'] = data.copy()
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
        'email_code': '邮箱验证码',
        'phone_code': '手机验证码',
        'phone_or_email': '手机或邮箱',
        'password': '密码',
        'old_password': '原始密码',
        'gender': '性别',
        'priority': '优先级',
        'task_type': '任务类型',
        'pages': '页码',
        'pages_file': '页码文件',

    }
    return maps[key] if key in maps else key


def allowed_keys(**kw):
    """申明需要哪些数据属性"""
    pass


def not_empty(**kw):
    """不允许为空以及空串"""
    code, message = e.not_allowed_empty
    errs = {k: (code, message % i18n_trans(k)) for k, v in kw.items() if not v}
    return errs or None


def not_both_empty(**kw):
    """不允许同时为空以及空串"""
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


def is_name(**kw):
    """ 检查是否为姓名。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, v):
        return {k: e.invalid_name}


def is_phone(**kw):
    """ 检查是否为手机。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^1[34578]\d{9}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_phone}


def is_email(**kw):
    """ 检查是否为邮箱。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, v):
        return {k: e.invalid_email}


def is_phone_or_email(**kw):
    """ 检查是否为手机或邮箱。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    email_regex = r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$'
    phone_regex = r'^1[34578]\d{9}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(email_regex, v) and not re.match(phone_regex, v):
        return {k: e.invalid_phone_or_email}


def is_password(**kw):
    """ 检查是否为密码。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^(?![0-9]+$)(?![a-zA-Z]+$)[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_password}


def is_priority(**kw):
    """ 检查是否为优先级。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[123]$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_priority}


def is_tripitaka(**kw):
    """ 检查是否为藏编码。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[A-Z]{1,2}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_tripitaka_code}


def is_volume(**kw):
    """ 检查是否为册编码。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[A-Z]{1,2}(_\d+)+$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_volume_code}


def is_sutra(**kw):
    """ 检查是否为经编码。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[A-Z]{1,2}\d{4,}$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_sutra_code}


def is_reel(**kw):
    """ 检查是否为卷编码。"""
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[A-Z]{1,2}\d{4,}_\d*$'
    # 值为空或空串时跳过而不检查
    if v and not re.match(regex, str(v)):
        return {k: e.invalid_reel_code}


def is_digit(**kw):
    """ 检查是否为数字。"""
    code, message = e.invalid_digit
    errs = {k: (code, '%s:%s' % (k, message)) for k, v in kw.items() if v and not re.match(r'^\d+$', str(v))}
    return errs or None


def between(min, max, **kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    code, message = e.invalid_range
    err = code, message % (i18n_trans(k), min, max)
    if v < min or v > max:
        return {k: err}


def in_list(lst, **kw):
    """检查是否在lst列表中"""
    k, v = list(kw.items())[0]
    if v:
        code, message = e.not_in_list
        err = code, message % (i18n_trans(k), lst)
        assert type(v) in [str, list]
        v = [v] if isinstance(v, str) else v
        not_in = [i for i in v if i not in lst]
        if not_in:
            return {k: err}


def has_fileds(fields, **kw):
    """检查是否有fields中的字段"""
    k, v = list(kw.items())[0]
    if v:
        need_fields = [r for r in fields if r not in v.keys()]
        if need_fields:
            err = e.tptk_field_error[0], '缺字段：%s' % ','.join(need_fields)
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
            if v is not None and collection.count_documents({k: v}) > 1:
                errs[k] = code, message % i18n_trans(k)
    return errs or None


def code_verify_timeout(collection=None, **kw):
    errs = {}
    email, email_code = kw.get('email'), kw.get('email_code')
    phone, phone_code = kw.get('phone'), kw.get('phone_code')

    if email and email_code and collection:
        code, message = e.code_wrong_or_timeout
        email_code = email_code.upper()
        r = collection.find_one(
            {"type": 'email', "data": email, "code": email_code,
             "stime": {"$gt": datetime.now() - timedelta(minutes=1)}}
        )
        if not r:
            errs['email_code'] = code, message % i18n_trans('email_code')

    if phone and phone_code and collection:
        code, message = e.code_wrong_or_timeout
        phone_code = phone_code.upper()
        r = collection.find_one(
            {"type": 'phone', "data": phone, "code": phone_code,
             "stime": {"$gt": datetime.now() - timedelta(minutes=1)}}
        )
        if not r:
            errs['phone_code'] = code, message % i18n_trans('phone_code')
    return errs or None
