#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

op_types = {
    'visit': '页面访问',
    'pick_{task_type}': '领取任务',
    'return_{task_type}': '退回任务',
    'submit_{task_type}': '提交任务',
    'publish_{task_type}': '发布任务',
    'save_do_{task_type}': '新任务保存',
    'save_update_{task_type}': '原任务保存',
    'save_edit_{task_type}': '任务修改保存',
    'withdraw_{task_type}': '撤回任务',
    'reset_{task_type}': '重置任务',
    'login_no_user': '账号不存在',
    'login_fail': '账号密码不对',
    'login_ok': '登录成功',
    'logout': '注销登录',
    'register': '注册账号',
    'change_user_profile': '修改用户信息',
    'change_role': '修改用户角色',
    'reset_password': '重置密码',
    'delete_user': '删除用户',
    'change_password': '修改个人密码',
    'change_profile': '修改个人信息',
}
re_map = []


def get_op_name(op_type):
    if not re_map:
        for k in op_types:
            re_map.append((re.compile(k.replace('{task_type}', '[a-z0-9_.]+')), k))
    for r, k in re_map:
        if r.match(op_type):
            return op_types[k]
