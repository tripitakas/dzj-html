#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler基类
@time: 2019/3/11
"""

from controller.handler.base import BaseHandler


class TaskHandler(BaseHandler):
    """
    任务Handler基类。
    1. 任务状态。
    任务数据未到位时，状态为“unready”。上传数据后，程序进行检查，如果满足发布条件，则状态置为“ready”。
    发布任务只能发布状态为“ready”的任务。如果没有前置任务，则直接发布，状态为“opened”；如果有前置任务，则悬挂，状态为“pending”。
    用户领取任务后，状态为“locked”，退回任务后，状态为“returned”，提交任务后，状态为“finished”。
    2. 前置任务
    任务配置表中定义了默认的前置任务。
    业务管理员在发布任务时，可以对前置任务进行修改，比如文字审定需要两次或者三次校对。发布任务后，任务的前置任务将记录在数据库中。
    如果任务包含前置任务，系统发布任务后，状态为“pending”。当前置任务状态都变为“finished”时，自动将当前任务发布为“opened”。
    3. 发布任务
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、页面集合（task_id）
    """

    default_page_size = 50

    """
    任务类型配置表。
    @name 任务名称
    @pre_tasks 前置任务列表
    @sub_task_types 子任务列表
    """
    task_types = {
        'cut_block_proof': {
            'name': '切栏校对',
        },
        'cut_block_review': {
            'name': '切栏审定',
            'pre_tasks': ['cut_block_proof'],
        },
        'cut_column_proof': {
            'name': '切列校对',
        },
        'cut_column_review': {
            'name': '切列审定',
            'pre_tasks': ['cut_column_proof'],
        },
        'cut_char_proof': {
            'name': '切字校对',
        },
        'cut_char_review': {
            'name': '切字审定',
            'pre_tasks': ['cut_char_proof'],
        },
        'char_order_proof': {
            'name': '字序校对',
            'pre_tasks': ['cut_char_review'],
        },
        'char_order_review': {
            'name': '字序审定',
            'pre_tasks': ['char_order_proof'],
        },
        'text_proof': {
            'name': '文字校对',
            'sub_task_types': {
                '1': {
                    'name': '校一',
                },
                '2': {
                    'name': '校二',
                },
                '3': {
                    'name': '校三',
                },
            }
        },
        'text_review': {
            'name': '文字审定',
            'pre_tasks': ['text_proof.1', 'text_proof.2', 'text_proof.3'],
        },
    }

    """
    将任务类型扁平化后，返回任务类型列表。
    如果是二级任务，则表示为task_type.sub_task_type。
    """
    @property
    def flat_types(self):
        types = []
        for k, v in self.task_types.items():
            if 'sub_task_types' not in v:
                types.append(k)
            else:
                for t in v['sub_task_types']:
                    types.append('%s.%s' % (k, t))
        return types

    """
    后置任务
    """
    @property
    def post_tasks(self):
        post_types = {}
        for k, v in self.task_types.items():
            if 'pre_tasks' in v:
                assert isinstance(v, list)
                post_types.update({t: k for t in v['pre_tasks']})
            elif 'sub_task_types' in v:
                for n, m in v['sub_task_types']:
                    if 'pre_tasks' in m:
                        assert isinstance(m, list)
                        post_types.update({t: k + '.' + n for t in m['pre_tasks']})
        return post_types

    """
    任务状态表
    """
    STATUS_UNREADY = 'unready'
    STATUS_READY = 'ready'
    STATUS_OPENED = 'opened'
    STATUS_PENDING = 'pending'
    STATUS_LOCKED = 'locked'
    STATUS_RETURNED = 'returned'
    STATUS_FINISHED = 'finished'
    task_statuses = {
        STATUS_UNREADY: '数据未就绪',
        STATUS_READY: '数据已就绪',
        STATUS_OPENED: '未领取',
        STATUS_PENDING: '等待前置任务',
        STATUS_LOCKED: '进行中',
        STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }
