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
"""
role_route_maps = {
    'user': {
        'name': '普通用户',
        'routes': {
            '/user/login': ['GET'],
            '/user/logout': ['GET'],
            '/user/register': ['GET'],
            '/user/profile': ['GET'],
        }
    },
    'cut_block_proof': {
        'name': '切栏校对员',
        'routes': {
            '/task/lobby/cut_block_proof': ['GET'],
            '/task/my/cut_block_proof': ['GET'],
            '/task/do/cut_block_proof/@task_id': ['GET', 'POST'],
        }
    },
    'cut_block_review': {
        'name': '切栏审定员',
        'routes': {
            '/task/lobby/cut_block_review': ['GET'],
            '/task/my/cut_block_review': ['GET'],
            '/task/do/cut_block_review/@task_id': ['GET', 'POST'],
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
        }

    },
    'text_review': {
        'name': '文字审定员',
        'routes': {
            '/task/lobby/text_review': ['GET'],
            '/task/my/text_review': ['GET'],
            '/task/do/text_review/@num/@task_id': ['GET', 'POST'],
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
        }
    },
}


def get_role_routes(role):
    """获取指定角色对应的route集合"""
    assert type(role) in [str, list]
    roles = [role] if type(role) == str else role
    routes = dict()
    for r in roles:
        routes.update(role_route_maps.get(r, {}).get('routes', {}))
        # 进一步查找嵌套角色
        for r0 in role_route_maps.get(r, {}).get('roles', []):
            routes.update(get_role_routes(r0))
    return routes


if __name__ == '__main__':
    for k, v in get_role_routes(['cut_expert', 'data_admin', 'task_admin']).items():
        print(k, v)
