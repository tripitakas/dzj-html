#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 角色和权限
@time: 2019/3/13
角色权限对应表，定义系统中的所有角色以及对应的route权限。
将属于同一业务的route分配给同一个角色，用户通过拥有角色来拥有对应的route权限。
角色可以嵌套定义，如下表中的切分专家和文字专家。
"""

import re

url_placeholder = {
    'task_type': r'[a-z0-9_.]+',
    'task_id': r'[A-Za-z0-9_]+',  # 对应page表的name字段
    'box_type': 'block|column|char',
    'num': r'\d+',
    'page_prefix': r'[A-Za-z0-9_]*',
    'page_kind': r'[a-z_]+',
    'tripitaka_id': r'[a-z]{3,}'
}

role_maps = {
    '单元测试用户': {
        'routes': {
            '/api/task/page/@task_id': ['GET'],
            '/api/task/pages/@page_kind': ['GET', 'POST'],
            '/api/task/unlock/@task_type/@page_prefix': ['GET'],
            '/api/user/list': ['GET'],
        }
    },
    '访客': {
        'remark': '任何人都可访问，无需登录',
        'routes': {
            '/api': ['GET'],
            '/api/code/(.+)': ['GET'],
            '/user/login': ['GET'],
            '/api/user/login': ['POST'],
            '/api/user/logout': ['GET'],
            '/user/register': ['GET'],
            '/api/user/register': ['POST'],
            '/api/user/upload_img':['POST'],
            '/task/do/char_order_proof/@task_id': ['GET'],  # 实现后再移到切字校对员里
        }
    },
    '普通用户': {
        'remark': '登录用户均可访问，无需授权',
        'routes': {
            '/': ['GET'],
            '/home': ['GET'],
            '/help': ['GET'],
            '/user/my/profile': ['GET'],
            '/api/user/my/profile': ['POST'],
            '/api/user/my/pwd': ['POST'],
            '/api/task/page/@task_id': ['GET'],
            '/tripitaka': ['GET'],
            '/tripitaka/@tripitaka_id': ['GET'],
            '/tripitaka/rs': ['GET'],
            '/api/task/unlock/@task_type/@page_prefix': ['POST'],
        }
    },
    '切栏校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/block_cut_proof': ['GET'],
            '/task/my/block_cut_proof': ['GET'],
            '/task/do/block_cut_proof/@task_id': ['GET', 'POST'],
            '/api/task/pick/block_cut_proof/@task_id': ['GET'],
            '/api/task/save/block_cut_proof': ['POST'],
        }
    },
    '切栏审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/block_cut_review': ['GET'],
            '/task/my/block_cut_review': ['GET'],
            '/task/do/block_cut_review/@task_id': ['GET', 'POST'],
            '/api/task/pick/block_cut_review/@task_id': ['GET'],
            '/api/task/save/block_cut_review': ['POST'],
        }
    },
    '切列校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/column_cut_proof': ['GET'],
            '/task/my/column_cut_proof': ['GET'],
            '/task/do/column_cut_proof/@task_id': ['GET', 'POST'],
            '/api/task/pick/column_cut_proof/@task_id': ['GET'],
            '/api/task/save/column_cut_proof': ['POST'],
        }
    },
    '切列审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/column_cut_review': ['GET'],
            '/task/my/column_cut_review': ['GET'],
            '/task/do/column_cut_review/@task_id': ['GET', 'POST'],
            '/api/task/pick/column_cut_review/@task_id': ['GET'],
            '/api/task/save/column_cut_review': ['POST'],
        }
    },
    '切字校对员': {
        'is_assignable': 'char_cut_proof',
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/char_cut_proof': ['GET'],
            '/task/my/char_cut_proof': ['GET'],
            '/task/do/char_cut_proof/@task_id': ['GET', 'POST'],
            '/api/task/pick/char_cut_proof/@task_id': ['GET'],
            '/api/task/save/char_cut_proof': ['POST'],
        }
    },
    '切字审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/char_cut_review': ['GET'],
            '/task/my/char_cut_review': ['GET'],
            '/task/do/char_cut_review/@task_id': ['GET', 'POST'],
            '/api/task/pick/char_cut_review/@task_id': ['GET'],
            '/api/task/save/char_cut_review': ['POST'],
        }
    },
    '切分专家': {
        'is_assignable': True,
        'roles': ['普通用户', '切栏校对员', '切栏审定员', '切列校对员', '切列审定员', '切字校对员', '切字审定员'],
    },
    '文字校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/text_proof': ['GET'],
            '/task/my/text_proof': ['GET'],
            '/task/do/text_proof/@num/@task_id': ['GET', 'POST'],
            '/api/task/pick/text_proof(\.[123])?/@task_id': ['GET'],
            '/api/task/save/text_proof/@num': ['POST'],
        }
    },
    '文字审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/lobby/text_review': ['GET'],
            '/task/my/text_review': ['GET'],
            '/task/do/text_review/@task_id': ['GET', 'POST'],
            '/api/task/pick/text_review/@task_id': ['GET'],
            '/api/task/save/text_review': ['POST'],
        }
    },
    '文字专家': {
        'is_assignable': True,
        'roles': ['普通用户', '文字校对员', '文字审定员'],
        'routes': {
            '/task/lobby/text_hard': ['GET'],
        }
    },
    '任务管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/admin/@task_type': ['GET'],
            '/task/admin/cut/status': ['GET'],
            '/task/admin/text/status': ['GET'],
            '/api/task/pages/@page_kind': ['GET', 'POST'],
            '/api/task/publish': ['POST'],
            '/api/task/unlock/@task_type/@page_prefix': ['GET'],
        }
    },
    '数据管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/data/tripitaka': ['GET'],
            '/data/envelop': ['GET'],
            '/data/volume': ['GET'],
            '/data/sutra': ['GET'],
            '/data/reel': ['GET'],
            '/data/page': ['GET'],
            '/user/statistic': ['GET'],
        }
    },
    '用户管理员': {
        'is_assignable': True,
        'routes': {
            '/user/admin': ['GET'],
            '/user/role': ['GET'],
            '/api/user/delete': ['POST'],
            '/api/user/profile': ['POST'],
            '/api/user/role': ['POST'],
            '/api/user/reset_pwd': ['POST'],
        }
    },
}

# 界面可分配的角色、切分审校和文字审校角色
assignable_roles = [role for role, v in role_maps.items() if v.get('is_assignable')]

def get_role_routes(role, routes=None):
    """
    获取指定角色对应的route集合
    :param role: 可以是一个或多个角色，多个角色为逗号分隔的字符串
    """
    assert type(role) == str, str(role)
    routes = dict() if routes is None else routes
    roles = [r.strip() for r in role.split(',')]
    for r in roles:
        for url, m in role_maps.get(r, {}).get('routes', {}).items():
            routes[url] = list(set(routes.get(url, []) + m))
        # 进一步查找嵌套角色
        for r0 in role_maps.get(r, {}).get('roles', []):
            get_role_routes(r0, routes)
    return routes


def can_access(role, path, method):
    """
    检查角色是否可以访问某个请求
    :param role: 可以是一个或多个角色，多个角色为逗号分隔的字符串
    :param path: 浏览器请求path
    :param method: http请求方法，如GET/POST
    """
    for holder, regex in url_placeholder.items():
        path = path.replace('@' + holder, '(%s)' % regex)
    route_accessible = get_role_routes(role)
    for _path, _method in route_accessible.items():
        for holder, regex in url_placeholder.items():
            _path = _path.replace('@' + holder, '(%s)' % regex)
        if (path == _path or re.match('^%s$' % _path, path) or re.match('^%s$' % path, _path)) and method in _method:
            return True
    return False


def get_route_roles(uri, method):
    roles = []
    for role in role_maps:
        if can_access(role, uri, method) and role not in roles:
            roles.append(role)
    return roles

