#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 模态类

class User(object):
    id = str
    name = str
    email = str
    password = str
    phone = int
    authority = str  # ACCESS_ALL 组合而成，逗号分隔
    gender = str
    image = str
    status = int
    create_time = str
    last_time = str
    old_password = str  # 修改密码临时用
    login_md5 = str  # 密码和权限的MD5码