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
    'shared_field': r'box|text',
    'article_id': r'[^/]{6,}',
    'oid': r'[a-z0-9]{24}',
    'task_id': r'[a-z0-9]{24}',
    'doc_id': r'[a-zA-Z]{2}_[_0-9]+',
    'char_name': r'[a-zA-Z]{2}_[_0-9]+',
    'page_name': r'[a-zA-Z]{2}_[_0-9]+',
    'page_prefix': r'[a-zA-Z]{2}[_0-9]*',
    'metadata': r'tripitaka|sutra|volume|reel|page|char',
    'cut_task': r'cut_proof|cut_review',
    'text_task': r'text_proof_\d|text_review',
    'ocr_task': r'ocr_box|ocr_text|upload_cloud|import_image',
    'task_type': r'ocr_\w+|cut_\w+|text_\w+|cluster_\w+|separate_\w+|upload_cloud|import_image',
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
            '/api/task/ready/@task_type': ['POST'],
            '/api/task/finish/@task_id': ['POST'],
            '/api/data/lock/@shared_field/@doc_id': ['POST'],
        }
    },
    '访客': {
        'is_assignable': False,
        'remark': '任何人都可访问，无需登录',
        'routes': {
            '/user/(login|register)': ['GET'],
            '/api/user/(login|logout|register|email_code|phone_code)': ['POST'],
            '/api/user/forget_pwd': ['POST'],
            '/article/@article_id': ['GET'],
            '/page/cut_edit/@page_name': ['GET'],
        }
    },
    '普通用户': {
        'is_assignable': False,
        'remark': '登录用户均可访问，无需授权',
        'routes': {
            '/': ['GET'],
            '/(home|help|announce)': ['GET'],
            '/task/sample/@task_type': ['GET'],
            '/user/my/profile': ['GET'],
            '/api/user/my/(pwd|profile|avatar)': ['POST'],
            '/tripitaka': ['GET'],
            '/tripitaka/@page_prefix': ['GET'],
            '/com/punctuate': ['GET'],
            '/api/com/punctuate': ['POST'],
            '/com/search': ['GET'],
            '/api/com/search': ['POST'],
        }
    },
    '工作人员': {
        'is_assignable': False,
        'remark': '工作人员公共请求',
        'roles': ['普通用户'],
        'routes': {
            '/api/session/config': ['POST'],
            '/task/@task_type/@task_id': ['GET'],
            '/api/task/return/@task_id': ['POST'],
            '/api/page/text/diff': ['POST'],
            '/api/task/text/detect_chars': ['POST'],
            '/api/page/cmp_txt/neighbor': ['POST'],
            '/page/@page_name': ['GET'],
            '/page/cut_view/@page_name': ['GET'],
            '/page/text_view/@page_name': ['GET'],
            '/api/data/unlock/@shared_field/@doc_id': ['POST'],
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
        'roles': ['切分校对员', '切分审定员', 'OCR校对员', 'OCR审定员'],
        'routes': {
            '/page/cut_edit/@page_name': ['GET'],
            '/api/page/cut_edit/@page_name': ['POST'],
        }
    },
    '文字校对员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/text_proof': ['GET'],
            '/api/task/pick/text_proof': ['POST'],
            '/api/task/pick/text_proof_@num': ['POST'],
            '/api/task/text_select/@page_name': ['POST'],
            '/task/(do|update|view)/text_proof_@num/@task_id': ['GET'],
            '/api/task/(do|update)/text_proof_@num/@task_id': ['POST'],
            '/page/cut_edit/@page_name': ['GET'],
            '/api/page/cut_edit/@page_name': ['POST'],
        }
    },
    '文字审定员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/task/(lobby|my)/text_review': ['GET'],
            '/api/task/pick/text_review': ['POST'],
            '/task/(do|update|view)/text_review/@task_id': ['GET'],
            '/api/task/(do|update)/text_review/@task_id': ['POST'],
            '/page/cut_edit/@page_name': ['GET'],
            '/api/page/cut_edit/@page_name': ['POST'],
        }
    },
    '聚类校对员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/char/@char_name': ['POST'],
            '/task/(lobby|my)/cluster_proof': ['GET'],
            '/api/task/pick/cluster_proof': ['POST'],
            '/task/(do|update|view)/cluster_proof/@task_id': ['GET'],
            '/api/task/(do|update)/cluster_proof/@task_id': ['POST'],
        }
    },
    '聚类审定员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/char/@char_name': ['POST'],
            '/task/(lobby|my)/cluster_review': ['GET'],
            '/api/task/pick/cluster_review': ['POST'],
            '/task/(do|update|view)/cluster_review/@task_id': ['GET'],
            '/api/task/(do|update)/cluster_review/@task_id': ['POST'],
        }
    },
    '分类校对员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/char/@char_name': ['POST'],
            '/task/(lobby|my)/separate_proof': ['GET'],
            '/api/task/pick/separate_proof': ['POST'],
            '/task/(do|update|view)/separate_proof/@task_id': ['GET'],
            '/api/task/(do|update)/separate_proof/@task_id': ['POST'],
        }
    },
    '分类审定员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/char/@char_name': ['POST'],
            '/task/(lobby|my)/separate_review': ['GET'],
            '/api/task/pick/separate_review': ['POST'],
            '/task/(do|update|view)/separate_review/@task_id': ['GET'],
            '/api/task/(do|update)/separate_review/@task_id': ['POST'],
        }
    },
    '文字专家': {
        'is_assignable': True,
        'roles': ['工作人员', '文字校对员', '文字审定员'],
        'routes': {
            '/task/(lobby|my)/text_hard': ['GET'],
            '/api/task/pick/text_hard': ['POST'],
            '/task/(do|update)/text_hard/@task_id': ['GET'],
            '/api/task/(do|update)/text_hard/@task_id': ['POST'],
            '/page/(text_edit|char_edit)/@page_name': ['GET'],
            '/api/page/text_edit/@page_name': ['POST'],
        }
    },
    '任务浏览员': {
        'is_assignable': True,
        'roles': ['工作人员'],
        'routes': {
            '/api/user/list': ['POST'],
            '/task/(page|char)/statistic': ['GET'],
            '/task/detail/@task_id': ['GET'],
            '/task/resume/page/@page_name': ['GET'],
            '/task/admin/(image|page|char)': ['GET'],
            '/task/browse/@task_type/@task_id': ['GET'],
        }
    },
    '任务管理员': {
        'is_assignable': True,
        'roles': ['工作人员', '任务浏览员'],
        'routes': {
            '/api/task/ready/@task_type': ['POST'],
            '/api/(page|char)/publish_task': ['POST'],
            '/api/task/publish/import': ['POST'],
            '/api/task/publish/(box|text)': ['POST'],
            '/api/task/republish/@task_id': ['POST'],
            '/api/task/(assign|delete|batch|remark)': ['POST'],
            '/api/data/admin/unlock/@shared_field/@doc_id': ['POST'],
        }
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
    '数据管理员': {
        'is_assignable': True,
        'roles': ['工作人员', 'OCR加工员'],
        'routes': {
            '/data/@metadata': ['GET'],
            '/api/data/@metadata': ['POST'],
            '/api/data/@metadata/delete': ['POST'],
            '/api/data/gen_js': ['POST'],
            '/page/(box|order|cmp_txt)/@page_name': ['GET'],
            '/page/(box|order|cmp_txt)/edit/@page_name': ['GET'],
            '/api/page/(box|order|cmp_txt)/@page_name': ['POST'],
            '/data/page/info/@page_name': ['GET'],
            '/data/char/statistic': ['GET'],
            '/api/data/page/export_char': ['POST'],
            '/api/data/page/source': ['POST'],
            '/api/data/char/source': ['POST'],
            '/api/char/gen_img': ['POST'],
            '/api/char/@char_name': ['POST'],
            '/char/browse': ['GET'],
        }
    },
    '文章管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/article': ['GET'],
            '/article/add': ['GET'],
            '/article/@article_id': ['GET'],
            '/article/update/@article_id': ['GET'],
            '/api/article/(add|update|delete)': ['POST'],
            '/php/imageUp.php': ['POST'],
        }
    },
    '用户管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/user/admin': ['GET'],
            '/user/admin/role': ['GET'],
            '/api/user/admin': ['POST'],
            '/api/user/admin/(delete|role|reset_pwd)': ['POST'],
        }
    },
    '系统管理员': {
        'is_assignable': True,
        'roles': ['普通用户'],
        'routes': {
            '/api': ['GET'],
            '/api/code/(.+)': ['GET'],
            '/admin/script': ['GET'],
            '/admin/oplog': ['GET'],
            '/admin/oplog/@oid': ['GET'],
            '/admin/oplog/latest': ['GET'],
            '/api/admin/oplog/delete': ['POST'],
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
