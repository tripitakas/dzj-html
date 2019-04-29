#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据校验类
@time: 2019/4/29
"""

import re

"""错误类型、代码及错误提示消息"""
not_allowed_empty = 1000, '不允许为空'
not_allowed_both_empty = 1001, r'%s和%s不允许同时为空'
invalid_name = 1002, '姓名应为2~5个汉字，或3~20个英文字母（可含空格和-）'
invalid_phone = 1003, '手机号码应为以1开头的11位数字'
invalid_email = 1004, '邮箱格式有误'
invalid_password = 1005, '密码应为6至18位由数字、字母和英文符号组成的字符串，不可以为纯数字或纯字母'
invalid_range = 1006, r'数据范围应为[%s, %s]'


def validate(data, rules):
    """
    数据校验主控函数
    :param data:  待校验的数据，一般是指从页面POST的dict类型的数据
    :param rules: 校验规则列表，每个rule是一个(func, para1, para2, ...)元组，其中，func是校验工具函数。关于para1、para2等参数：
                  1. 如果是字符串格式，则表示data的属性，将data[para1]数据作为参数传递给func函数
                  2. 如果不是字符串格式，则直接作为参数传递给func函数
    :return: 如果校验有误，则返回校验错误代码列表。无误，则无返回值。
    """
    errs = []
    kw_funcs = [not_empty, not_both_empty]  # 关键字参数函数
    for rule in rules:
        func = rule[0]
        if func in kw_funcs:
            paras = {para: data.get(para) for para in rule[1:]}
            ret = func(**paras)
        else:
            paras = [data.get(para) if isinstance(para, str) else para for para in rule[1:]]
            ret = func(*paras)
        if ret:
            if isinstance(ret, list):
                errs.extend(ret)
            else:
                errs.append(ret)
    return errs or None


def not_empty(**kw):
    errs = []
    for k, v in kw.items():
        if not v:
            code, message = not_allowed_empty
            message = k + message
            errs.append((code, message))
    return errs or None


def not_both_empty(**kw):
    assert len(kw) == 2
    code, message = not_allowed_both_empty
    k1, k2 = kw.keys()
    v1, v2 = kw[k1], kw[k2]
    if not v1 and not v2:
        return code, message % (k1, k2)


def is_name(name):
    re_name = re.compile(br'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'.decode('raw_unicode_escape'))
    if not re_name.match(name):
        return invalid_name


def is_phone(phone):
    re_phone = re.compile(r'^1\d{10}$')
    if not re_phone.match(phone):
        return invalid_phone


def is_email(email):
    re_email = re.compile(r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$')
    if not re_email.match(email):
        return invalid_email


def is_password(password):
    re_password = re.compile(r'^(?![0-9]+$)(?![a-zA-Z]+$)[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$')
    if not re_password.match(password):
        return invalid_password


def between(value, min, max):
    code, message = invalid_range
    if value < min or value > max:
        return code, message % (min, max)


if __name__ == '__main__':
    # TODO: 这段测试可移到单元测试中
    data = {'name': '', 'phone': '1234567890', 'email': 'user#rs.com', 'password': '123456', 'age': 8}
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
