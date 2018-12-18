#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/10/23
"""


class User(object):
    id = str
    name = str
    email = str
    password = str
    authority = str  # ACCESS_ALL 组合而成，逗号分隔
    create_time = str
    last_time = str
    old_password = str  # 修改密码临时用
    login_md5 = str  # 密码和权限的MD5码


ACCESS_PROOF1 = '一校'
ACCESS_MANAGER = '管理员'
ACCESS_ALL = [ACCESS_PROOF1, ACCESS_MANAGER]

authority_map = dict(proof1=ACCESS_PROOF1, manager=ACCESS_MANAGER)
