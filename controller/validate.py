#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据校验类
@time: 2019/4/29
"""

import re

"""错误类型、代码及错误提示消息"""
not_allowed_empty = 1000, '不允许为空'
not_allowed_both_empty = 1001, '不允许同时为空'
invalid_name = 1002, '姓名应为2~5个汉字，或3~20个英文字母（可含空格和-）'
invalid_phone = 1003, '手机号码格式有误'
invalid_email = 1004, '邮箱格式有误'
invalid_password = 1005, '密码应为6至18位由数字、字母和英文符号组成的字符串，不可以为纯数字或纯字母'
invalid_range = 1006, '数据范围应为[%s, %s]'


def validate(data, rules):
    """
    数据校验主控函数
    :param data:  待校验的数据，一般是指从页面POST的dict类型的数据
    :param rules: 校验规则列表，每个rule是一个(func, para1, para2, ...)元组，其中，func是校验工具函数。关于para1、para2等参数：
                  1. 如果是字符串格式，则表示data的属性，将data[para1]数据作为参数传递给func函数
                  2. 如果不是字符串格式，则直接作为参数传递给func函数
    :return: 如果校验有误，则返回校验错误(key, error_code, message)或列表。其中，key为字符串或字符串列表。无误，则无返回值。
    """
    errs = []
    for rule in rules:
        func = rule[0]
        kw = {para: data.get(para) for para in rule[1:] if isinstance(para, str)}
        args = [para for para in rule[1:] if not isinstance(para, str)]
        ret = func(*args, **kw)
        if ret:
            errs.append(ret)
    return errs or None


def not_empty(**kw):
    empty_keys = [k for k, v in kw.items() if not v]
    empty_keys = empty_keys[0] if len(empty_keys) == 1 else empty_keys
    code, message = not_allowed_empty
    if empty_keys:
        return empty_keys, code, message


def not_both_empty(**kw):
    assert len(kw) == 2
    k1, k2 = kw.keys()
    v1, v2 = kw[k1], kw[k2]
    code, message = not_allowed_both_empty
    if not v1 and not v2:
        return [k1, k2], code, message


def is_name(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'
    code, message = invalid_name
    if v and not re.match(regex, v):
        return k, code, message


def is_phone(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^1[34578]\d{9}$'
    code, message = invalid_phone
    if v and not re.match(regex, v):
        return k, code, message


def is_email(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$'
    code, message = invalid_email
    if v and not re.match(regex, v):
        return k, code, message


def is_password(**kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    regex = r'^(?![0-9]+$)(?![a-zA-Z]+$)[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$'
    code, message = invalid_password
    if v and not re.match(regex, v):
        return k, code, message


def between(min, max, **kw):
    assert len(kw) == 1
    k, v = list(kw.items())[0]
    code, message = invalid_range
    if v < min or v > max:
        return k, code, message % (min, max)


if __name__ == '__main__':
    # TODO: 这段测试可移到单元测试中
    data = {'name': '', 'phone': '1234567890', 'email': '', 'password': '', 'age': 8}
    rules = [
        (not_empty, 'name', 'password'),
        (not_both_empty, 'phone', 'email'),
        (is_name, 'name'),
        (is_phone, 'phone'),
        (is_email, 'email'),
        (is_password, 'password'),
        (between, 'age', 10, 100)
    ]

    errs = validate(data, rules)
    for err in errs:
        print(err)
