#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 角色和权限
@time: 2019/3/13
角色权限对应表，定义系统中的所有角色、名称以及对应的route权限。
系统中每一个url请求，无论是来自浏览器路径栏的，还是来自js发起的Ajax请求，都对应一个访问路径route。
将属于同一类业务的route集合分配给同一个角色，系统中所有的route分配给不同的的角色。用户通过拥有角色来拥有对应的route权限。
角色可以嵌套定义，如下表中的切分专家和文字专家。
访客的路由适用于普通用户，普通用户的路由适用于任何用户。
"""

import re

url_placeholder = {
    'user_id': r'[A-Za-z0-9_]+',
    'task_type': r'[a-z0-9_.]+',
    'task_id': r'[A-Za-z0-9_]+',  # 对应page表的name字段
    'sutra_id': r'[a-zA-Z]{2}',
    'num': r'\d+',
    'page_prefix': r'[A-Za-z0-9_]*',
    'page_kind': r'[a-z_]+',
}

role_maps = {
    'testing': {
        'name': '单元测试用户',
        'routes': {
            '/api/@task_type/@task_id': ['GET'],
            '/api/page/@task_id': ['GET'],
            '/api/pages/@page_kind': ['GET', 'POST'],
            '/api/unlock/@task_type/@page_prefix': ['GET'],
            '/api/user/list': ['GET'],
        }
    },
    'anonymous': {
        'name': '访客',
        'routes': {
            '/api': ['GET'],
            '/api/code/(.+)': ['GET'],
            '/api/options/([a-z_]+)': ['GET'],
            '/user/login': ['GET'],
            '/user/register': ['GET'],
            '/api/user/login': ['POST'],
            '/api/user/register': ['POST'],
            '/api/user/logout': ['GET'],
        }
    },
    'default_user': {
        'name': '普通用户',
        'remark': '注册用户均可访问，无需授权',
        'routes': {
            '/': ['GET'],
            '/home': ['GET'],
            '/user/logout': ['GET'],
            '/user/profile': ['GET'],
            '/api/user/change': ['POST'],
            '/api/pwd/change': ['POST'],
            '/tripitaka': ['GET'],
            '/tripitaka/@tripitaka_id': ['GET'],
            '/tripitaka/rs': ['GET'],
        }
    },
    'block_cut_proof': {
        'name': '切栏校对员',
        'routes': {
            '/task/lobby/block_cut_proof': ['GET'],
            '/task/my/block_cut_proof': ['GET'],
            '/task/do/block_cut_proof/@task_id': ['GET', 'POST'],
            '/api/pick/block_cut_proof/@task_id': ['GET'],
            '/api/save/block_cut_proof': ['POST'],
        }
    },
    'block_cut_review': {
        'name': '切栏审定员',
        'routes': {
            '/task/lobby/block_cut_review': ['GET'],
            '/task/my/block_cut_review': ['GET'],
            '/task/do/block_cut_review/@task_id': ['GET', 'POST'],
            '/api/pick/block_cut_review/@task_id': ['GET'],
            '/api/save/block_cut_review': ['POST'],
        }
    },
    'column_cut_proof': {
        'name': '切列校对员',
        'routes': {
            '/task/lobby/column_cut_proof': ['GET'],
            '/task/my/column_cut_proof': ['GET'],
            '/task/do/column_cut_proof/@task_id': ['GET', 'POST'],
            '/api/pick/column_cut_proof/@task_id': ['GET'],
            '/api/save/column_cut_proof': ['POST'],
        }
    },
    'column_cut_review': {
        'name': '切列审定员',
        'routes': {
            '/task/lobby/column_cut_review': ['GET'],
            '/task/my/column_cut_review': ['GET'],
            '/task/do/column_cut_review/@task_id': ['GET', 'POST'],
            '/api/pick/column_cut_review/@task_id': ['GET'],
            '/api/save/column_cut_review': ['POST'],
        }
    },
    'char_cut_proof': {
        'name': '切字校对员',
        'routes': {
            '/task/lobby/char_cut_proof': ['GET'],
            '/task/my/char_cut_proof': ['GET'],
            '/task/do/char_cut_proof/@task_id': ['GET', 'POST'],
            '/api/pick/char_cut_proof/@task_id': ['GET'],
            '/api/save/char_cut_proof': ['POST'],
        }
    },
    'char_cut_review': {
        'name': '切字审定员',
        'routes': {
            '/task/lobby/char_cut_review': ['GET'],
            '/task/my/char_cut_review': ['GET'],
            '/task/do/char_cut_review/@task_id': ['GET', 'POST'],
            '/api/pick/char_cut_review/@task_id': ['GET'],
            '/api/save/char_cut_review': ['POST'],
        }
    },
    'cut_expert': {
        'name': '切分专家',
        'roles': ['block_cut_proof', 'char_cut_proof', 'column_cut_proof',
                  'block_cut_review', 'char_cut_review', 'column_cut_review'],
    },
    'text_proof': {
        'name': '文字校对员',
        'routes': {
            '/task/lobby/text_proof': ['GET'],
            '/task/my/text_proof': ['GET'],
            '/task/do/text_proof/@num/@task_id': ['GET', 'POST'],
            '/api/pick/text_proof_(1|2|3)/@task_id': ['GET'],
        }
    },
    'text_review': {
        'name': '文字审定员',
        'routes': {
            '/task/lobby/text_review': ['GET'],
            '/task/my/text_review': ['GET'],
            '/task/do/text_review/@num/@task_id': ['GET', 'POST'],
            '/api/pick/text_review/@task_id': ['GET'],
        }
    },
    'text_expert': {
        'name': '文字专家',
        'roles': ['text_proof', 'text_review', ],
        'routes': {
            '/task/lobby/text_hard': ['GET'],
        }
    },
    'task_admin': {
        'name': '任务管理员',
        'routes': {
            '/task/admin/@task_type': ['GET'],
            '/task/admin/cut/status': ['GET'],
            '/task/admin/text/status': ['GET'],
            '/api/start/@page_prefix': ['POST'],
            '/api/pages/@page_kind': ['GET', 'POST'],
            '/api/task/publish/@task_type': ['POST'],
            '/api/unlock/@task_type/@page_prefix': ['GET'],
        }
    },
    'data_admin': {
        'name': '数据管理员',
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
    'user_admin': {
        'name': '用户管理员',
        'routes': {
            '/user/admin': ['GET'],
            '/user/role': ['GET'],
            '/api/pwd/reset/@user_id': ['POST'],
            '/api/user/list': ['GET'],
            '/api/user/remove': ['POST'],
        }
    },
}

# 获取指定角色对应的名称
role_name_maps = {k: v['name'] for k, v in role_maps.items()}


def get_role_routes(role, routes={}):
    """
    获取指定角色对应的route集合
    :param role: 可以是一个或多个角色，多个角色为逗号分隔的字符串
    """
    assert type(role) == str
    roles = [r.strip() for r in role.split(',')]
    for r in roles:
        for url, m in role_maps.get(r, {}).get('routes', {}).items():
            routes[url] = list(set(routes.get(url, []) + m))
        # 进一步查找嵌套角色
        for r0 in role_maps.get(r, {}).get('roles', ''):
            get_role_routes(r0, routes)
    return routes


def can_access(role, uri, method):
    route_accessible = get_role_routes(role)
    for _uri, _method in route_accessible.items():
        for holder, regex in url_placeholder.items():
            _uri = _uri.replace('@' + holder, regex)
        if re.match('^%s$' % _uri, uri) and method in _method:
            return True
    return False


def get_route_roles(uri, method):
    roles = []
    for role in role_maps:
        if can_access(role, uri, method) and role not in roles:
            roles.append(role)
    return roles


if __name__ == '__main__':
    # TODO: 这段测试可移到单元测试中，校验 role_maps
    if can_access('block_cut_proof', '/task/do/block_cut_proof/GL_1_1_1', 'GET'):
        print('can access')
    else:
        print('can not access')

    print(get_route_roles('/task/do/block_cut_proof/GL_1_1', 'GET'))

    for k, v in get_role_routes('cut_expert').items():
        print(k, v)
