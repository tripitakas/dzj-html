#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 模态类

class User(object):
    id = str
    name = str
    email = str
    password = str
    phone = int
    roles = str  # 用户角色
    gender = str
    image = str
    create_time = str
    last_time = str
    old_password = str  # 修改密码临时用
