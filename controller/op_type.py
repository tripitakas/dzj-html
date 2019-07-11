#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

op_types = {
    'visit': dict(name='页面访问'),
    'pick_{task_type}': dict(name='领取任务', trends=True),
    'return_{task_type}': dict(name='退回任务', trends=True),
    'submit_{task_type}': dict(name='提交任务', trends=True),
    'publish_{task_type}': dict(name='发布任务', trends=True),
    'save_do_{task_type}': dict(name='新任务保存'),
    'save_update_{task_type}': dict(name='原任务保存'),
    'save_edit_{task_type}': dict(name='任务修改保存'),
    'sel_cmp_{task_type}': dict(name='比对文本保存'),
    'withdraw_{task_type}': dict(name='撤回任务', trends=True),
    'reset_{task_type}': dict(name='重置任务'),
    'login_no_user': dict(name='账号不存在'),
    'login_fail': dict(name='账号密码不对'),
    'login_ok': dict(name='登录成功', trends=True),
    'logout': dict(name='注销登录'),
    'register': dict(name='注册账号', trends=True),
    'change_user_profile': dict(name='修改用户信息'),
    'change_role': dict(name='修改用户角色'),
    'reset_password': dict(name='重置密码'),
    'delete_user': dict(name='删除用户'),
    'change_password': dict(name='修改个人密码'),
    'change_profile': dict(name='修改个人信息'),
}
re_map = []


def get_op_def(op_type):
    if not re_map:
        for k in op_types:
            re_map.append((re.compile(k.replace('{task_type}', '[a-z0-9_.]+')), k))
    for r, k in re_map:
        if r.match(op_type):
            return op_types[k]


def get_op_name(op_type):
    r = get_op_def(op_type)
    return r and r['name']


def op_in_recent_trends(op_type):
    r = get_op_def(op_type)
    return r and r.get('trends')
