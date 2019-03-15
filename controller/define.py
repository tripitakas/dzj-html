#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 后端公共定义类
@time: 2019/3/10
"""
import model.user as u

url_placeholder = {
    'user_id': r'[A-Za-z0-9_]+',
    'task_type': r'[a-z0-9_.]+',
    'task_id': r'[A-Za-z0-9_]+',  # 对应page表的name字段
    'sutra_id': r'[a-zA-Z]{2}',
    'num': r'\d+',
    'task-kind': r'[a-z_]+',
    'task_type_ex': u.re_task_type + '|cut_proof|cut_review|cut|text',
    'page_prefix': r'[A-Za-z0-9_]*',
    'page_kind': r'[a-z_]+',
    'box-type': 'block|column|char',
}
