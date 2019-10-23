#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 角色和权限
@time: 2019/3/13
"""

import re

# url占位符
url_placeholder = {
    'num': r'\d+',
    'task_type': r'cut_proof|cut_review|ocr_proof|ocr_review|text_\w+',
    'cut_task': r'cut_proof|cut_review',
    'text_task': r'text_proof_\d|text_review',
    'data_task': r'ocr|upload_cloud|import_image',
    'task_id': r'\w{24}',
    'doc_id': r'[a-zA-Z]{2}_[0-9_]+',
    'collection': r'tripitaka|sutra|volume|reel|page',
    'shared_field': r'box|text',
    'box_type': 'block|column|char',
    'page_code': r'[A-Z]{2}[fb0-9_]*',
    'page_name': r'[a-zA-Z]{2}_[0-9_]+',
    'page_prefix': r'[a-zA-Z]{2}[0-9_]*',
    'img_file': '[A-Za-z0-9._-]+',
    'user_code': '[A-Za-z0-9]+',
}

""" 角色权限对应表，定义系统中的所有角色以及对应的route权限。
    将属于同一业务的route分配给同一个角色，用户通过拥有角色来拥有对应的route权限。
    角色可以嵌套定义，如下表中的切分专家和文字专家。字段说明：
    routes：角色可以访问的权限集合；
    roles：角色所继承的父角色； 
    is_assignable：角色是否可被分配。 
"""
role_route_maps = {
    '单元测试用户': {
        'is_assignable': False,
        'routes': {
            '/api/user/list': ['GET'],
            '/api/task/ready/@task_type': ['POST'],
            '/api/task/finish/@task_type/@task_id': ['POST'],
            '/api/data/lock/@shared_field/@doc_id': ['POST'],
        }
    },
    '访客': {
        'is_assignable': False,
        'remark': '任何人都可访问，无需登录',
        'routes': {
            '/api': ['GET'],
            '/api/code/(.+)': ['GET'],
            '/user/(login|register)': ['GET'],
            '/api/user/(login|logout|register|email_code|phone_code)': ['POST'],
            '/api/user/forget_pwd': ['POST'],
        }
    },
    '普通用户': {
        'is_assignable': False,
        'remark': '登录用户均可访问，无需授权',
        'routes': {
            '/': ['GET'],
            '/home': ['GET'],
            '/help': ['GET'],
            '/user/my/profile': ['GET'],
            '/api/user/my/(pwd|profile|avatar)': ['POST'],
            '/tripitakas': ['GET'],
            '/tripitaka/rs': ['GET'],
            '/t/@page_code': ['GET'],
            '/ocr/recognize': ['GET'],
            '/api/ocr/recognize': ['POST'],
            '/ocr/@img_file': ['GET'],
            '/punc/punctuate': ['GET'],
            '/api/punc/punctuate': ['POST'],
            '/search/cbeta': ['GET'],
            '/api/search/cbeta': ['POST'],
            '/api/cut/gen_char_id': ['POST'],
            '/task/@task_type/@task_id': ['GET'],
        }
    },
    '切分校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/cut_proof': ['GET'],
            '/api/task/pick/cut_proof': ['POST'],
            '/task/(do|update)/cut_proof/@task_id': ['GET'],
            '/api/task/(do|update|return)/cut_proof/@task_id': ['POST'],
            '/api/data/unlock/box/@page_name': ['POST'],
        }
    },
    '切分审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/cut_review': ['GET'],
            '/api/task/pick/cut_review': ['POST'],
            '/task/(do|update)/cut_review/@task_id': ['GET'],
            '/api/task/(do|update|return)/cut_review/@task_id': ['POST'],
            '/api/data/unlock/box/@page_name': ['POST'],
        }
    },
    '切分专家': {
        'is_assignable': True,
        'roles': ['切分校对员', '切分审定员', 'OCR校对员', 'OCR审定员'],
        'routes': {
            '/data/edit/box/@page_name': ['GET'],
            '/api/data/edit/box/@page_name': ['POST'],
            '/api/data/unlock/box/@page_name': ['POST'],
        }
    },
    '文字校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/text_proof': ['GET'],
            '/api/task/pick/text_proof': ['POST'],
            '/api/task/pick/text_proof_@num': ['POST'],
            '/task/(do|update)/text_proof_@num/@task_id': ['GET'],
            '/api/task/text_get_compare/@page_name': ['POST'],
            '/api/task/text_compare_neighbor': ['POST'],
            '/api/task/(do|update|return)/text_proof_@num/@task_id': ['POST'],
            '/data/edit/box/@page_name': ['GET'],
            '/api/data/edit/box/@page_name': ['POST'],
            '/api/data/unlock/box/@page_name': ['POST'],
            '/api/data/unlock/text/@page_name': ['POST'],
        }
    },
    '文字审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/text_review': ['GET'],
            '/api/task/pick/text_review': ['POST'],
            '/task/(do|update)/text_review/@task_id': ['GET'],
            '/api/task/(do|update|return)/text_review/@task_id': ['POST'],
            '/data/edit/box/@page_name': ['GET'],
            '/api/data/edit/box/@page_name': ['POST'],
            '/api/data/unlock/box/@page_name': ['POST'],
            '/api/data/unlock/text/@page_name': ['POST'],
        }
    },
    '文字专家': {
        'is_assignable': True,
        'roles': ['普通用户', '文字校对员', '文字审定员'],
        'routes': {
            '/task/(lobby|my)/text_hard': ['GET'],
            '/api/task/pick/text_hard': ['POST'],
            '/task/(do|update)/text_hard/@task_id': ['GET'],
            '/api/task/(do|update|return)/text_hard/@task_id': ['POST'],
            '/data/edit/text/@page_name': ['GET'],
            '/api/data/edit/text/@page_name': ['POST'],
            '/api/data/unlock/text/@page_name': ['POST'],
        }
    },
    '任务管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/api/task/publish': ['POST'],
            '/task/page/@page_name': ['GET'],
            '/task/admin/@task_type': ['GET'],
            '/api/task/ready/@task_type': ['POST'],
            '/api/user/@task_type': ['POST'],
            '/api/task/(assign|retrieve|delete)/@task_type': ['POST'],
        }
    },
    '数据处理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/api/data/(pick|submit)/@data_task': ['POST']
        }
    },
    '数据管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/data/@collection': ['GET'],
            '/api/data/pages': ['POST'],
            '/api/data/@collection': ['POST'],
            '/api/data/@collection/(upload|delete)': ['POST'],
            '/api/data/publish/@data_task': ['POST'],
            '/data/import_image': ['GET'],
            '/api/data/delete/import_image': ['POST'],
        }
    },
    '用户管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/user/statistic': ['GET'],
            '/user/(admin|role)': ['GET'],
            '/api/user/(delete|role|profile|reset_pwd)': ['POST'],
        }
    },
}


def get_assignable_roles():
    """可分配给用户的角色"""
    return [role for role, v in role_route_maps.items() if v.get('is_assignable')]


def can_access(role, path, method):
    """
    检查角色是否可以访问某个请求
    :param role: 可以是一个或多个角色，多个角色为逗号分隔的字符串
    :param path: 浏览器请求path
    :param method: http请求方法，如GET/POST
    """

    def match_exclude(p, exclude):
        for holder, regex in url_placeholder.items():
            if holder not in exclude:
                p = p.replace('@' + holder, '(%s)' % regex)
        route_accessible = get_role_routes(role)
        for _path, _method in route_accessible.items():
            for holder, regex in url_placeholder.items():
                if holder not in exclude:
                    _path = _path.replace('@' + holder, '(%s)' % regex)
            if (p == _path or re.match('^%s$' % _path, p) or re.match('^%s$' % p, _path)) and method in _method:
                return True
            parts = re.search(r'\(([a-z|]+)\)', _path)
            if parts:
                whole, parts = parts.group(0), parts.group(1).split('|')
                for ps in parts:
                    ps = _path.replace(whole, ps)
                    if (p == ps or re.match('^%s$' % ps, p) or re.match('^%s$' % p, ps)) and method in _method:
                        return True

    if re.search('./$', path):
        path = path[:-1]
    if match_exclude(path, []):
        return True
    if match_exclude(path, ['page_name', 'num']):
        return True
    return False


def get_role_routes(roles, routes=None):
    """
    获取指定角色对应的route集合
    :param role: 可以是一个或多个角色，多个角色为逗号分隔的字符串
    """
    assert type(roles) in [str, list]
    if type(roles) == str:
        roles = [r.strip() for r in roles.split(',')]
    routes = dict() if routes is None else routes
    for r in roles:
        for url, m in role_route_maps.get(r, {}).get('routes', {}).items():
            routes[url] = list(set(routes.get(url, []) + m))
        # 进一步查找嵌套角色
        for r0 in role_route_maps.get(r, {}).get('roles', []):
            get_role_routes(r0, routes)
    return routes


def get_route_roles(uri, method):
    """获取能访问route(uri, method)的所有角色"""
    roles = []
    for role in role_route_maps:
        if can_access(role, uri, method) and role not in roles:
            roles.append(role)
    return roles


def get_all_roles(user_roles):
    """获取所有角色（包括嵌套角色）"""
    if isinstance(user_roles, str):
        user_roles = [u.strip() for u in user_roles.split(',')]
    roles = list(user_roles)
    for role in user_roles:
        sub_roles = role_route_maps.get(role, {}).get('roles')
        if sub_roles:
            roles.extend(sub_roles)
            for _role in sub_roles:
                roles.extend(get_all_roles(_role))
    return list(set(roles))
