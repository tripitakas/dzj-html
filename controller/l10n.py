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
    'inserted_char': '已插入字码',
    'existed_char': '已存在字码',
    'invalid_char': '无效字码',
    'invalid_pages': '无效页码',
    'extract_img': '生成字图',
    'success_char': '字图生成成功',
    'fail_char': '字图生成失败',
    'exist_char': '字图已存在',
    'success_column': '列图生成成功',
    'fail_column': '列图生成失败',
}
