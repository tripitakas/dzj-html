#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 角色和权限
@time: 2019/3/13
"""

import re

# url占位符，注意不要带括号
url_placeholder = {
    'num': r'\d+',
    'user_code': '[A-Za-z0-9]+',
    'img_file': '[A-Za-z0-9._-]+',
    'oid': r'[a-z0-9]{24}',
    'op_type': r'[a-z_]+',
    'article_id': r'[^/]{6,}',
    'task_id': r'[a-z0-9]{24}',
    'doc_id': r'[a-zA-Z]{2}_[_0-9]+',
    'char_name': r'[a-zA-Z]{2}_[_0-9]+',
    'page_name': r'[a-zA-Z]{2}_[_0-9]+',
    'tripitaka_code': r'[a-zA-Z]{2}',
    'page_prefix': r'[a-zA-Z]{2}[_0-9]*',
    'metadata': r'tripitaka|sutra|volume|reel|variant',
    'ocr_task': r'ocr_box|ocr_txt|upload_cloud',
    'page_task': r'cut_proof|cut_review|txt_match|find_cmp',
    'cluster_task': r'cluster_proof|cluster_review|rare_proof|rare_review',
    'task_type': r'ocr_\w+|cut_\w+|txt_\w+|cluster_\w+|rare_\w+|txt_match|find_cmp',
}

""" 
角色权限对应表。定义系统中的所有角色以及对应的route权限，将属于同一业务的route分配给同一个角色，
用户通过拥有角色来拥有对应的route权限。角色可以嵌套定义，如下表中的切分专家和文字专家。字段说明：
roles：角色所继承的父角色；
routes：角色可以访问的权限集合；
is_assignable：角色是否可被分配。
"""
role_route_maps = {
    '单元测试用户': {
        'is_assignable': False,
        'routes': {
            '/api/user/list': ['POST'],
            '/api/task/init': ['POST'],
            '/api/task/finish/@oid': ['POST'],
        }
    },
    '访客': {
        'is_assignable': False,
        'remark': '任何人都可访问，无需登录',
        'routes': {
            '/article/@article_id': ['GET'],
            '/user/(login|register)': ['GET'],
            '/api/user/forget_pwd': ['POST'],
            '/api/user/(login|logout|register|email_code|phone_code)': ['POST'],
        }
    },
    '普通用户': {
        'is_assignable': False,
        'remark': '登录用户均可访问，无需授权',
        'routes': {
            '/': ['GET'],
            '/user/my/profile': ['GET'],
            '/(home|help|announce)': ['GET'],
            '/task/sample/@task_type': ['GET'],
            '/api/user/my/(pwd|profile|avatar)': ['POST'],
            '/tripitaka/list': ['GET'],
            '/(tripitaka|tptk)/@page_prefix': ['GET'],
            '/(sutra|reel|volume)/@tripitaka_code': ['GET'],
            '/com/search': ['GET'],
            '/com/punctuate': ['GET'],
            '/api/com/search': ['POST'],
            '/api/com/punctuate': ['POST'],
        }
    },
    '工作人员': {
        'is_assignable': False,
        'remark': '工作人员公共链接',
        'roles': ['普通用户'],
        'routes': {
            '/api/session/config': ['POST'],
            '/task/@task_type/@task_id': ['GET'],
            '/api/task/return/@task_id': ['POST'],
            '/page/@page_name': ['GET'],
            '/page/box/@page_name': ['GET'],
            '/api/page/box/@page_name': ['POST'],
            '/api/page/txt_match/diff': ['POST'],
            '/api/page/find_cmp/neighbor': ['POST'],
            '/api/page/txt/(diff|detect_chars)': ['POST'],
            '/char/@char_name': ['GET'],
            '/api/chars/(txt|txt_type|box)': ['POST'],
            '/api/char/(txt|box)/@char_name': ['POST'],
        }
    },
    '切分校对员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/cut_proof': ['GET'],
            '/api/task/pick/cut_proof': ['POST'],
            '/task/(do|update)/cut_proof/@task_id': ['GET'],
            '/api/task/(do|update)/cut_proof/@task_id': ['POST'],
        }
    },
    '切分审定员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/cut_review': ['GET'],
            '/api/task/pick/cut_review': ['POST'],
            '/task/(do|update)/cut_review/@task_id': ['GET'],
            '/api/task/(do|update)/cut_review/@task_id': ['POST'],
        }
    },
    '切分专家': {
        'is_assignable': True,
        'roles': ['切分校对员', '切分审定员'],
        'routes': {}
    },
    '文字预处理员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/(find_cmp|txt_match)': ['GET'],
            '/api/task/pick/(find_cmp|txt_match)': ['POST'],
            '/task/(do|update)/(find_cmp|txt_match)/@task_id': ['GET'],
            '/api/task/(do|update)/(find_cmp|txt_match)/@task_id': ['POST'],
        }
    },
    '聚类校对员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/cluster_proof': ['GET'],
            '/api/task/pick/cluster_proof': ['POST'],
            '/task/(do|update)/cluster_proof/@task_id': ['GET'],
            '/api/task/(do|update)/cluster_proof/@task_id': ['POST'],
            '/api/data/variant': ['POST'],
        }
    },
    '聚类审定员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/cluster_review': ['GET'],
            '/api/task/pick/cluster_review': ['POST'],
            '/task/(do|update)/cluster_review/@task_id': ['GET'],
            '/api/task/(do|update)/cluster_review/@task_id': ['POST'],
            '/api/data/variant': ['POST'],
        }
    },
    '生僻校对员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/rare_proof': ['GET'],
            '/api/task/pick/rare_proof': ['POST'],
            '/task/(do|update)/rare_proof/@task_id': ['GET'],
            '/api/task/(do|update)/rare_proof/@task_id': ['POST'],
            '/api/data/variant': ['POST'],
        }
    },
    '生僻审定员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/rare_review': ['GET'],
            '/api/task/pick/rare_review': ['POST'],
            '/task/(do|update)/rare_review/@task_id': ['GET'],
            '/api/task/(do|update)/rare_review/@task_id': ['POST'],
            '/api/data/variant': ['POST'],
        }
    },
    '文字专家': {
        'is_assignable': True,
        'roles': ['工作人员', '文字预处理员', '聚类校对员', '聚类审定员', '生僻校对员', '生僻审定员'],
        'routes': {}
    },
    'OCR加工员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/task/init': ['POST'],
            '/task/(lobby|my)/@ocr_task': ['GET'],
            '/api/task/pick/@ocr_task': ['POST'],
            '/api/task/(fetch_many|confirm_fetch)/@ocr_task': ['POST'],
            '/api/task/submit/@ocr_task': ['POST'],
            '/api/data/@metadata/upload': ['POST'],
        }
    },
    '任务浏览员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/user/list': ['POST'],
            '/task/(page|char)/statistic': ['GET'],
            '/task/info/@task_id': ['GET'],
            '/page/task/resume/@page_name': ['GET'],
            '/task/browse/@task_type/@task_id': ['GET'],
        }
    },
    '任务管理员': {
        'is_assignable': True,
        'roles': ['工作人员', '任务浏览员'],
        'routes': {
            '/(page|char)/task/(list|statistic)': ['GET'],
            '/api/task/ready/@task_type': ['POST'],
            '/api/(page|char)/task/publish': ['POST'],
            '/api/task/publish/import': ['POST'],
            '/api/task/republish/@task_id': ['POST'],
            '/api/task/(assign|delete|batch|remark)': ['POST'],
            '/api/data/admin/unlock/@shared_field/@doc_id': ['POST'],
        }
    },
    '数据管理员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/data/@metadata': ['GET'],
            '/api/data/@metadata': ['POST'],
            '/api/variant/delete': ['POST'],
            '/api/data/@metadata/delete': ['POST'],
            '/page/(list|statistic)': ['GET'],
            '/page/(browse|info)/@page_name': ['GET'],
            '/api/page': ['POST'],
            '/page/(box|order|find_cmp|ocr_col|cmp_txt|txt|text_proof|txt_proof)/@page_name': ['GET'],
            '/api/page/(delete|source|start_gen_chars|start_check_match)': ['POST'],
            '/api/page/(box|order|find_cmp|cmp_txt|txt_match)/@page_name': ['POST'],
            '/char/(list|browse|statistic)': ['GET'],
            '/api/char/(delete|source|extract_img)': ['POST'],
        }
    },
    '文章管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/article/@article_id': ['GET'],
            '/article/update/@article_id': ['GET'],
            '/article/(add|admin)': ['GET'],
            '/api/article/admin/(add|update|delete)': ['POST'],
            '/php/imageUp.php': ['POST'],
        }
    },
    '用户管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/user/admin': ['GET'],
            '/api/user/admin': ['POST'],
            '/api/user/admin/(delete|reset_pwd)': ['POST'],
            '/user/role': ['GET'],
            '/api/user/role': ['POST'],
        }
    },
    '系统管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/api': ['GET'],
            '/api/code/(.+)': ['GET'],
            '/sys/script': ['GET'],
            '/api/data/gen_js': ['POST'],
            '/sys/upload_oss': ['GET'],
            '/sys/(oplog|log)': ['GET'],
            '/sys/oplog/latest': ['GET'],
            '/sys/oplog/latest/@op_type': ['GET'],
            '/sys/(oplog|log)/@oid': ['GET'],
            '/api/sys/oplog/status/@oid': ['POST'],
            '/api/sys/(oplog|log)/delete': ['POST'],
            '/api/sys/upload_oss/(char|column)': ['POST'],
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

    if match_exclude(path, []):
        return True
    if match_exclude(path, ['page_name', 'num']):
        return True
    if re.search('./$', path):
        return can_access(role, path[:-1], method)
    return False


def get_role_routes(roles, routes=None):
    """ 获取指定角色对应的route集合
    :param roles: 可以是一个或多个角色，多个角色为逗号分隔的字符串
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
