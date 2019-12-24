#!/usr/bin/env python
# -*- coding: utf-8 -*-

import controller.validate as v
from controller.model import Model


class User(Model):
    collection = 'user'
    fields = [
        {'id': 'img', 'name': '头像'},
        {'id': 'name', 'name': '姓名'},
        {'id': 'gender', 'name': '性别', 'input_type': 'radio', 'options': ['男', '女']},
        {'id': 'email', 'name': '邮箱'},
        {'id': 'phone', 'name': '手机'},
        {'id': 'password', 'name': '密码'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
    ]
    rules = [
        (v.not_empty, 'name', 'password'),
        (v.not_both_empty, 'email', 'phone'),
        (v.is_name, 'name'),
        (v.is_email, 'email'),
        (v.is_phone, 'phone'),
        (v.is_password, 'password'),
    ]
    primary = '_id'

    page_title = '用户管理'
    search_tips = '请搜索用户名、手机和邮箱'
    search_fields = ['name', 'email', 'phone']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields if f['id'] not in ['img', 'password']]
    modal_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                         options=f.get('options', []))
                    for f in fields if f['id'] not in ['img', 'create_time', 'updated_time']]

    operations = [  # 列表包含哪些批量操作
        {'operation': 'btn-add', 'label': '新增用户'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]

    actions = [  # 列表单条记录包含哪些操作
        {'action': 'btn-update', 'label': '修改'},
        {'action': 'btn-remove', 'label': '删除'},
        {'action': 'btn-reset-pwd', 'label': '重置密码'},
    ]
