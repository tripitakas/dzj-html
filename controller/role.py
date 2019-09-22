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
    'num': r'\d+',
    'task_type': r'[a-z]+_cut_[a-z]+|text_\w+|ocr_\w+',
    'page_code': r'[A-Z]{2}[fb0-9_]*',
    'page_name': r'[a-zA-Z]{2}_[0-9_]+',
    'page_prefix': r'[a-zA-Z]{2}[0-9_]*',
    'box_type': 'block|column|char',
    'img_file': '[A-Za-z0-9._-]+',
}

""" 角色列表。针对每个角色定义：routes，角色可以访问的权限集合；roles，角色所继承的父角色；is_assignable，角色是否可被分配 """
role_maps = {
    '单元测试用户': {
        'is_assignable': False,
        'routes': {
            '/api/user/list': ['GET'],
            '/api/task/page/@page_name': ['GET'],
            '/api/task/ready_pages/@task_type': ['POST'],
            '/api/data/submit_ocr/@img_file': ['POST'],
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
            '/data/ocr': ['GET'],
            '/data/ocr/@img_file': ['GET'],
            '/api/data/ocr': ['POST'],
            '/data/punctuation': ['GET'],
            '/api/data/punctuation': ['POST'],
            '/data/cbeta/search': ['GET'],
            '/api/data/cbeta/search': ['POST'],
            '/task/@task_type/@page_name': ['GET'],
            '/api/data/gen_char_id': ['POST'],
            '/api/task/page/@page_name': ['GET'],

            # 下列只读浏览页面暂时允许普通用户访问
            '/task/block_cut_proof/@page_name': ['GET'],
            '/task/column_cut_proof/@page_name': ['GET'],
            '/task/char_cut_proof/@page_name': ['GET'],
            '/task/char_cut_proof/order/@page_name': ['GET'],
            '/task/char_cut_review/order/@page_name': ['GET'],
            '/task/text_proof_@num/@page_name': ['GET'],
            '/task/text_review/@page_name': ['GET'],
        }
    },
    '切栏校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/block_cut_proof': ['GET'],
            '/api/task/pick/block_cut_proof': ['POST'],
            '/task/(do|update)/block_cut_proof/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/block_cut_proof/@page_name': ['POST'],
        }
    },
    '切栏审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/block_cut_review': ['GET'],
            '/api/task/pick/block_cut_review': ['POST'],
            '/task/(do|update)/block_cut_review/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/block_cut_review/@page_name': ['POST'],
        }
    },
    '切列校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/column_cut_proof': ['GET'],
            '/api/task/pick/column_cut_proof': ['POST'],
            '/task/(do|update)/column_cut_proof/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/column_cut_proof/@page_name': ['POST'],
            '/data/edit/blocks/@page_name': ['GET'],
            '/api/data/edit/blocks/@page_name': ['POST'],
        }
    },
    '切列审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/column_cut_review': ['GET'],
            '/api/task/pick/column_cut_review': ['POST'],
            '/task/(do|update)/column_cut_review/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/column_cut_review/@page_name': ['POST'],
            '/data/edit/blocks/@page_name': ['GET'],
            '/api/data/edit/blocks/@page_name': ['POST'],
        }
    },
    '切字校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/char_cut_proof': ['GET'],
            '/api/task/pick/char_cut_proof': ['POST'],
            '/task/(do|update)/char_cut_proof/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/char_cut_proof/@page_name': ['POST'],
            '/task/(do|update)/char_cut_proof/order/@page_name': ['GET'],
            '/data/edit/(blocks|columns)/@page_name': ['GET'],
            '/api/data/edit/(blocks|columns)/@page_name': ['POST'],
        }
    },
    '切字审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/char_cut_review': ['GET'],
            '/api/task/pick/char_cut_review': ['POST'],
            '/task/(do|update)/char_cut_review/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/char_cut_review/@page_name': ['POST'],
            '/task/(do|update)/char_cut_review/order/@page_name': ['GET'],
            '/api/task/(do|update)/char_cut_review/order/@page_name': ['POST'],
            '/data/edit/(blocks|columns)/@page_name': ['GET'],
            '/api/data/edit/(blocks|columns)/@page_name': ['POST'],
        }
    },
    'OCR校对员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/ocr_proof': ['GET'],
            '/api/task/pick/ocr_proof': ['POST'],
            '/task/(do|update)/ocr_proof/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/ocr_proof/@page_name': ['POST'],
            '/task/(do|update)/ocr_proof/order/@page_name': ['GET'],
        }
    },
    'OCR审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/ocr_review': ['GET'],
            '/api/task/pick/ocr_review': ['POST'],
            '/task/(do|update)/ocr_review/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/ocr_review/@page_name': ['POST'],
            '/task/(do|update)/ocr_review/order/@page_name': ['GET'],
            '/api/task/(do|update)/ocr_review/order/@page_name': ['POST'],
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
            '/task/(lobby|my)/text_proof': ['GET'],
            '/api/task/pick/text_proof': ['POST'],
            '/api/task/pick/text_proof_@num': ['POST'],
            '/api/task/text_proof/get_cmp/@page_name': ['POST'],
            '/api/task/text_proof/get_cmp_neighbor': ['POST'],
            '/task/(do|update)/text_proof_@num/find_cmp/@page_name': ['GET'],
            '/api/task/(do|update)/text_proof_@num/find_cmp/@page_name': ['POST'],
            '/task/(do|update)/text_proof_@num/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/text_proof_@num/@page_name': ['POST'],
            '/data/edit/(blocks|columns|chars|char_order)/@page_name': ['GET'],
            '/api/data/edit/(blocks|columns|chars|char_order)/@page_name': ['POST'],
        }
    },
    '文字审定员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/(lobby|my)/text_review': ['GET'],
            '/api/task/pick/text_review': ['POST'],
            '/task/(do|update)/text_review/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/text_review/@page_name': ['POST'],
            '/data/edit/(blocks|columns|chars|char_order)/@page_name': ['GET'],
            '/api/data/edit/(blocks|columns|chars|char_order)/@page_name': ['POST'],
        }
    },
    '文字专家': {
        'is_assignable': True,
        'roles': ['普通用户', '文字校对员', '文字审定员'],
        'routes': {
            '/task/(lobby|my)/text_hard': ['GET'],
            '/api/task/pick/text_hard': ['POST'],
            '/task/(do|update)/text_hard/@page_name': ['GET'],
            '/api/task/(do|update|return|unlock)/text_hard/@page_name': ['POST'],
            '/data/edit/text/@page_name': ['GET'],
            '/api/data/edit/text/@page_name': ['POST'],
        }
    },
    '任务管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/task/info/@page_name': ['GET'],
            '/task/admin/@task_type': ['GET'],
            '/task/admin/(cut|text)/status': ['GET'],
            '/api/task/ready_pages/@task_type': ['POST'],
            '/api/task/publish': ['POST'],
            '/api/task/publish/@page_prefix': ['POST'],
            '/api/task/(withdraw|reset)/@task_type/@page_name': ['POST'],
        }
    },
    '数据管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/data/(tripitaka|volume|sutra|reel|page)': ['GET'],
            '/api/data/(tripitaka|volume|sutra|reel|page)': ['POST'],
            '/api/data/(tripitaka|volume|sutra|reel|page)/upload': ['POST'],
            '/api/data/(tripitaka|volume|sutra|reel|page)/delete': ['POST'],
            '/api/data/submit_ocr/@img_file': ['POST'],
            '/api/data/submit_ocr/@img_file': ['GET'],
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


def get_route_roles(uri, method):
    roles = []
    for role in role_maps:
        if can_access(role, uri, method) and role not in roles:
            roles.append(role)
    return roles


def get_all_roles(user_roles):
    if isinstance(user_roles, str):
        user_roles = [u.strip() for u in user_roles.split(',')]
    roles = list(user_roles)
    for role in user_roles:
        sub_roles = role_maps.get(role, {}).get('roles')
        if sub_roles:
            roles.extend(sub_roles)
            for _role in sub_roles:
                roles.extend(get_all_roles(_role))
    return list(set(roles))
