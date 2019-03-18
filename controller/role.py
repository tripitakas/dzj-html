#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 角色和权限
@time: 2019/3/13
"""

"""
角色权限对应表，定义系统中的所有角色、名称以及对应的route权限。
系统中每一个url请求，无论是来自浏览器路径栏的，还是来自js发起的Ajax请求，都对应一个访问路径route。
将属于同一类业务的route集合分配给同一个角色，系统中所有的route分配给不同的的角色。用户通过拥有角色来拥有对应的route权限。
角色可以嵌套定义，如下表中的切分专家和文字专家。
访客的路由适用于普通用户，普通用户的路由适用于任何用户。
"""
role_route_maps = {
    'testing': {
        'name': '自动测试免登录',
        'routes': {
            '/api/@task_type/@task_id': ['GET'],
            '/api/page/@task_id': ['GET'],
            '/api/pages/@page_kind': ['GET', 'POST'],
            '/api/unlock/@task_ex_type/@page_prefix': ['GET'],
            '/api/user/list': ['GET'],
        }
    },
    'anonymous': {
        'name': '访客',
        'routes': {
            '/api': ['GET'],
            '/api/code/(.+)': ['GET'],
            '/api/options/(\w+)': ['GET'],
            '/user/login': ['GET'],
            '/user/register': ['GET'],

            '/api/user/login': ['POST'],
            '/api/user/register': ['POST'],
            '/api/user/logout': ['GET'],
        }
    },
    'user': {
        'name': '普通用户',
        'routes': {
            '/': ['GET'],
            '/home': ['GET'],
            '/user/logout': ['GET'],
            '/user/profile': ['GET'],
            '/api/user/change': ['POST'],
            '/api/page/@task_id': ['GET'],
            '/dzj_@task-kind_history.html': ['GET'],
            '/api/pwd/change': ['POST'],
            '/task/my/@task_type': ['GET'],
            '/tripitaka': ['GET'],
            '/tripitaka/@tripitaka_id': ['GET'],
            '/tripitaka/rs': ['GET'],
        }
    },
    'cut_proof': {
        'name': '切分校对员',
        'roles': ['user'],
        'routes': {
            '/api/pick/@box-type_cut_proof/@task_id': ['GET'],
            '/dzj_@box-type_cut_proof/@task_id': ['GET'],
            '/api/save/@box-type_cut_proof': ['POST'],
        }
    },
    'cut_review': {
        'name': '切分审定员',
        'roles': ['user'],
        'routes': {
            '/api/pick/@box-type_cut_review/@task_id': ['GET'],
            '/dzj_@box-type_cut_review/@task_id': ['GET'],
            '/api/save/@box-type_cut_review': ['POST'],
        }
    },
    'block_cut_proof': {
        'name': '切栏校对员',
        'roles': ['cut_proof'],
        'routes': {
            '/task/lobby/block_cut_proof': ['GET'],
            '/task/my/block_cut_proof': ['GET'],
            '/task/do/block_cut_proof/@task_id': ['GET', 'POST'],
        }
    },
    'block_cut_review': {
        'name': '切栏审定员',
        'roles': ['cut_review'],
        'routes': {
            '/task/lobby/block_cut_review': ['GET'],
            '/task/my/block_cut_review': ['GET'],
            '/task/do/block_cut_review/@task_id': ['GET', 'POST'],
        }
    },
    'column_cut_proof': {
        'name': '切列校对员',
        'roles': ['cut_proof'],
        'routes': {
            '/task/lobby/column_cut_proof': ['GET'],
            '/task/my/column_cut_proof': ['GET'],
            '/task/do/column_cut_proof/@task_id': ['GET', 'POST'],
        }
    },
    'column_cut_review': {
        'name': '切列审定员',
        'roles': ['cut_review'],
        'routes': {
            '/task/lobby/column_cut_review': ['GET'],
            '/task/my/column_cut_review': ['GET'],
            '/task/do/column_cut_review/@task_id': ['GET', 'POST'],
        }
    },
    'char_cut_proof': {
        'name': '切字校对员',
        'roles': ['cut_proof'],
        'routes': {
            '/task/lobby/char_cut_proof': ['GET'],
            '/task/my/char_cut_proof': ['GET'],
            '/task/do/char_cut_proof/@task_id': ['GET', 'POST'],
        }
    },
    'char_cut_review': {
        'name': '切字审定员',
        'roles': ['cut_review'],
        'routes': {
            '/task/lobby/char_cut_review': ['GET'],
            '/task/my/char_cut_review': ['GET'],
            '/task/do/char_cut_review/@task_id': ['GET', 'POST'],
        }
    },
    'cut_expert': {
        'name': '切分专家',
        'roles': ['block_cut_proof', 'char_cut_proof', 'column_cut_proof',
                  'block_cut_review', 'char_cut_review', 'column_cut_review'],
    },
    'text_proof': {
        'name': '文字校对员',
        'roles': ['user'],
        'routes': {
            '/task/lobby/text_proof': ['GET'],
            '/task/my/text_proof': ['GET'],
            '/task/do/text_proof/@num/@task_id': ['GET', 'POST'],
            '/dzj_chars': ['GET'],
            '/dzj_char/@task_id': ['GET'],
            '/api/pick/text_proof_(1|2|3)/@task_id': ['GET'],
        }
    },
    'text_review': {
        'name': '文字审定员',
        'roles': ['user'],
        'routes': {
            '/task/lobby/text_review': ['GET'],
            '/task/my/text_review': ['GET'],
            '/task/do/text_review/@num/@task_id': ['GET', 'POST'],
            '/dzj_char_check.html': ['GET'],
            '/dzj_char/@task_id': ['GET'],
            '/api/pick/text_review/@task_id': ['GET'],
        }
    },
    'text_expert': {
        'name': '文字专家',
        'roles': ['user', 'text_proof', 'text_review', ],
        'routes': {
            '/task/lobby/text_hard': ['GET'],
        }
    },
    'task_admin': {
        'name': '任务管理员',
        'roles': ['user'],
        'routes': {
            '/task/admin/@task_type': ['GET'],
            '/dzj_task_cut_status.html': ['GET'],
            '/dzj_task_char_status.html': ['GET'],
            '/task/admin/cut/status': ['GET'],
            '/task/admin/text/status': ['GET'],
            '/api/start/@page_prefix': ['POST'],
            '/api/pages/@page_kind': ['GET', 'POST'],
            '/api/task/publish/@task_type': ['POST'],
            '/api/unlock/@task_ex_type/@page_prefix': ['GET'],
        }
    },
    'data_admin': {
        'name': '数据管理员',
        'roles': ['user'],
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
    'manager': {
        'name': '超级管理员',
        'roles': ['user', 'data_admin', 'task_admin', 'text_expert', 'cut_expert'],
        'routes': {
            '/user/admin': ['GET'],
            '/user/role': ['GET'],
            '/api/pwd/reset/@user_id': ['POST'],
            '/api/user/list': ['GET'],
            '/api/user/remove': ['POST'],
        }
    },
}


def get_role_routes(role, routes=None, exclude_roles=None):
    """获取指定角色对应的route集合"""
    assert type(role) in [str, list]
    roles = (role_route_maps.keys() if role == 'any' else [role]) if type(role) == str else role
    routes = dict() if routes is None else routes
    for r in roles:
        for url, m in role_route_maps.get(r, {}).get('routes', {}).items():
            routes[url] = list(set(routes.get(url, []) + m))
        # 进一步查找嵌套角色
        for r0 in role_route_maps.get(r, {}).get('roles', []):
            if not exclude_roles or r0 not in exclude_roles:
                get_role_routes(r0, routes, exclude_roles=exclude_roles)
    return routes


def get_route_roles(route, method):
    roles = []
    roles_used = []
    for role in (['user', 'cut_proof', 'cut_review'] + list(role_route_maps.keys())):
        if method in get_role_routes(role, exclude_roles=roles_used).get(route, []):
            if role not in roles:
                roles.append(role)
        roles_used.append(role)
    return roles


if __name__ == '__main__':
    for k, v in get_role_routes(['cut_expert']).items():
        print(k, v)  # TODO: 这段测试可移到单元测试中，校验 role_route_maps
