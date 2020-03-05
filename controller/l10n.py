#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 本地化
@time: 2020/3/5
"""


def _t(key):
    return l10n.get(key) or key


l10n = {
    'gen_chars': '生成字表',
    'inserted': '已插入',
    'existed': '已存在',
    'invalid': '无效数据',
    'invalid_pages': '无效页码',
}
