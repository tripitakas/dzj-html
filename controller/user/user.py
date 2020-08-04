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
        {'id': 'agent', 'name': '浏览器类型'},
    ]
    hide_fields = ['agent']
    rules = [
        (v.not_empty, 'name', 'password'),
        (v.not_both_empty, 'email', 'phone'),
        (v.is_name, 'name'),
        (v.is_email, 'email'),
        (v.is_phone, 'phone'),
        (v.is_password, 'password'),
    ]
    primary = '_id'

    search_tips = '请搜索用户名、手机和邮箱'
    search_fields = ['name', 'email', 'phone']
