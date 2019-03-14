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
            '/api/pages/@page_kind': ['GET'],
            '/api/unlock/@task_type_ex/@page_prefix': ['GET'],
        }
    },
    'anonymous': {
        'name': '访客',
        'routes': {
            '/api': ['GET'],
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
            '/dzj_@task-kind_history.html': ['GET'],
        }
    },
    'cut_block_proof': {
        'name': '切栏校对员',
        'routes': {
            '/task/lobby/cut_block_proof': ['GET'],
            '/task/my/cut_block_proof': ['GET'],
            '/task/do/cut_block_proof/@task_id': ['GET', 'POST'],
            '/dzj_cut.html': ['GET'],
            '/dzj_@box-type_cut_proof/@task_id': ['GET'],
        }
    },
    'cut_block_review': {
        'name': '切栏审定员',
        'routes': {
            '/task/lobby/cut_block_review': ['GET'],
            '/task/my/cut_block_review': ['GET'],
            '/task/do/cut_block_review/@task_id': ['GET', 'POST'],
            '/dzj_cut_check.html': ['GET'],
            '/dzj_@box-type_cut_review/@task_id': ['GET'],
        }
    },
    'cut_column_proof': {
        'name': '切列校对员',
        'routes': {
            '/task/lobby/cut_column_proof': ['GET'],
            '/task/my/cut_column_proof': ['GET'],
            '/task/do/cut_column_proof/@task_id': ['GET', 'POST'],
        }
    },
    'cut_column_review': {
        'name': '切列审定员',
        'routes': {
            '/task/lobby/cut_column_review': ['GET'],
            '/task/my/cut_column_review': ['GET'],
            '/task/do/cut_column_review/@task_id': ['GET', 'POST'],
        }
    },
    'cut_char_proof': {
        'name': '切字校对员',
        'routes': {
            '/task/lobby/cut_char_proof': ['GET'],
            '/task/my/cut_char_proof': ['GET'],
            '/task/do/cut_char_proof/@task_id': ['GET', 'POST'],
        }
    },
    'cut_char_review': {
        'name': '切字审定员',
        'routes': {
            '/task/lobby/cut_char_review': ['GET'],
            '/task/my/cut_char_review': ['GET'],
            '/task/do/cut_char_review/@task_id': ['GET', 'POST'],
        }
    },
    'cut_expert': {
        'name': '切分专家',
        'roles': [
            'cut_block_proof', 'cut_block_review',
            'cut_column_proof', 'cut_column_review',
            'cut_char_proof', 'cut_char_review',
        ],
    },
    'text_proof': {
        'name': '文字校对员',
        'routes': {
            '/task/lobby/text_proof': ['GET'],
            '/task/my/text_proof': ['GET'],
            '/task/do/text_proof/@num/@task_id': ['GET', 'POST'],
            '/dzj_chars': ['GET'],
            '/dzj_char/@task_id': ['GET'],
        }

    },
    'text_review': {
        'name': '文字审定员',
        'routes': {
            '/task/lobby/text_review': ['GET'],
            '/task/my/text_review': ['GET'],
            '/task/do/text_review/@num/@task_id': ['GET', 'POST'],
            '/dzj_char_check.html': ['GET'],
            '/dzj_char/@task_id': ['GET'],
        }
    },
    'text_expert': {
        'name': '文字专家',
        'roles': ['text_proof', 'text_review', ],
    },
    'task_admin': {
        'name': '任务管理员',
        'routes': {
            '/task/admin/cut_block_proof': ['GET'],
            '/task/admin/cut_block_review': ['GET'],
            '/task/admin/cut_column_proof': ['GET'],
            '/task/admin/cut_column_review': ['GET'],
            '/task/admin/cut_char_proof': ['GET'],
            '/task/admin/cut_char_review': ['GET'],
            '/task/admin/text_proof': ['GET'],
            '/task/admin/text_review': ['GET'],

            '/api/start/@page_prefix': ['POST'],
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
    'manager': {
        'name': '超级管理员',
        'routes': {
            '/user/admin': ['GET'],
            '/user/role': ['GET'],
            '/user/statistic': ['GET'],
        }
    },
}


def get_role_routes(role, routes=None):
    """获取指定角色对应的route集合"""
    assert type(role) in [str, list]
    roles = [role] if type(role) == str else role
    routes = dict() if routes is None else routes
    for r in roles:
        for url, m in role_route_maps.get(r, {}).get('routes', {}).items():
            routes[url] = list(set(routes.get(url, []) + m))
        # 进一步查找嵌套角色
        for r0 in role_route_maps.get(r, {}).get('roles', []):
            get_role_routes(r0, routes)
    return routes


if __name__ == '__main__':
    for k, v in get_role_routes(['cut_expert', 'data_admin', 'task_admin']).items():
        print(k, v)  # TODO: 这段测试可移到单元测试中，校验 role_route_maps
