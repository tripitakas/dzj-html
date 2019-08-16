#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

page_kinds = {'GL': '高丽藏', 'JX': '嘉兴藏', 'QL': '乾隆藏', 'YB': '永乐北藏'}

op_types = {
    'visit': dict(name='页面访问'),
    'pick_{task_type}': dict(name='领取任务', trends=True, msg='领取了{page_kind}{task_type}任务'),
    'return_{task_type}': dict(name='退回任务', trends=True, msg='退回了{page_kind}{task_type}任务'),
    'submit_{task_type}': dict(name='提交任务', trends=True, msg='完成了{page_kind}{task_type}任务'),
    'publish_{task_type}': dict(name='发布任务', trends=True, msg='发布了{count}个{task_type}任务'),
    'save_do_{task_type}': dict(name='新任务保存'),
    'save_update_{task_type}': dict(name='原任务保存'),
    'save_edit_{task_type}': dict(name='任务修改保存'),
    'sel_cmp_{task_type}': dict(name='比对文本保存'),
    'withdraw_{task_type}': dict(name='撤回任务', trends=True, msg='撤回了{page_name}{task_type}任务'),
    'reset_{task_type}': dict(name='重置任务', trends=True, msg='重置了{page_name}{task_type}任务'),
    'auto_unlock': dict(name='自动回收任务'),
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
    'add_tripitaka': dict(name='新增藏数据'),
    'update_tripitaka': dict(name='修改藏数据'),
    'delete_tripitaka': dict(name='删除藏数据'),
    'upload_tripitaka': dict(name='上传藏数据'),
    'add_volume': dict(name='新增册数据'),
    'update_volume': dict(name='修改册数据'),
    'delete_volume': dict(name='删除册数据'),
    'upload_volume': dict(name='上传册数据'),
    'add_sutra': dict(name='新增经数据'),
    'update_sutra': dict(name='修改经数据'),
    'delete_sutra': dict(name='删除经数据'),
    'upload_sutra': dict(name='上传经数据'),
    'add_reel': dict(name='新增卷数据'),
    'update_reel': dict(name='修改卷数据'),
    'delete_reel': dict(name='删除卷数据'),
    'upload_reel': dict(name='上传卷数据'),
}
re_map = []


def get_op_def(op_type, params=None):
    if not re_map:
        for k in op_types:
            re_map.append((re.compile(k.replace('{task_type}', '([a-z0-9_]+)')), k))
    for r, k in re_map:
        if r.match(op_type):
            if params is not None:
                v = r.findall(op_type)
                if v and 'task_type' in k:
                    params['task_type'] = v[0]
            return op_types[k]


def get_op_name(op_type):
    r = get_op_def(op_type)
    return r and r['name']


def op_in_recent_trends(op_type):
    r = get_op_def(op_type)
    return r and r.get('trends')
