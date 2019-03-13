#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler基类
@time: 2019/3/11
"""

from controller.base.base import BaseHandler


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

    @property
    def flat_task_types(self):
        """
        将任务类型扁平化后，返回任务类型列表。
        如果是二级任务，则表示为task_type.sub_task_type。
        """
        types = []
        for k, v in self.task_types.items():
            if 'sub_task_types' not in v:
                types.append(k)
            else:
                for t in v['sub_task_types']:
                    types.append('%s.%s' % (k, t))
        return types

    @property
    def task_type_names(self):
        type_names = {}
        for k, v in self.task_types.items():
            type_names[k] = v['name']
            if 'sub_task_types' in v:
                for k1, v1 in v['sub_task_types'].items():
                    type_names['%s.%s' % (k, k1)] = '%s.%s' % (v['name'], v1['name'])
        return type_names

    @property
    def text_task_names(self):
        return {
            'cut_block_proof': '切栏校对',
            'cut_block_review': '切栏审定',
            'cut_column_proof': '切列校对',
            'cut_column_review': '切列审定',
            'cut_char_proof': '切字校对',
            'cut_char_review': '切字审定'
        }

    @property
    def cut_task_names(self):
        return {
            'text_proof.1': '文字校一',
            'text_proof.2': '文字校二',
            'text_proof.3': '文字校三',
            'text_review': '文字审定'
        }

    @property
    def post_tasks(self):
        """
        后置任务
        """
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

    # 任务状态表
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
        STATUS_OPENED: '已发布未领取',
        STATUS_PENDING: '等待前置任务',
        STATUS_LOCKED: '进行中',
        STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }

    def get_next_task_todo(self, task_type):
        """ 获取下一个代办任务。如果有未完成的任务，则优先分配。如果没有，则从任务大厅中自动分配。 """
        pass

    def get_tasks_info_by_type(self, task_type, task_status=None, page_size='', page_no=1):
        """
        获取指定类型、状态的任务列表
        :param task_status: 可以是str或者list。如果为空，则查询所有记录。
        """
        assert task_type in self.task_types.keys()
        assert task_status is None or type(task_status) in [str, list]

        if type(task_status) == list:
            task_status = {"$in": task_status}

        if 'sub_task_types' in self.task_types[task_type]:
            sub_types = self.task_types[task_type]['sub_task_types'].keys()
            conditions = {
                '$or': [{'%s.%s.status' % (task_type, t): task_status} for t in sub_types]
            }
        else:
            conditions = {'%s.status' % task_type: task_status}

        if task_status is None:
            conditions = {}

        fields = {'name': 1, task_type: 1}

        page_size = self.default_page_size if page_size == '' else page_size
        pages = self.db.page.find(conditions, fields).limit(page_size).skip(page_size * (page_no - 1))
        return pages

    def get_my_tasks_by_type(self, task_type, page_size='', page_no=1):
        """
        获取我的任务列表
        """
        assert task_type in self.task_types.keys()

        user_id = self.current_user.id

        if 'sub_task_types' in self.task_types[task_type]:
            sub_types = self.task_types[task_type]['sub_task_types'].keys()
            conditions = {
                '$or': [{'%s.%s.picked_by' % (task_type, t): user_id} for t in sub_types]
            }
        else:
            conditions = {'%s.picked_by' % task_type: user_id}

        fields = {'name': 1, task_type: 1}

        page_size = self.default_page_size if page_size == '' else page_size
        pages = self.db.page.find(conditions, fields).limit(page_size).skip(page_size * (page_no - 1))
        return pages


    def get_tasks_info(self, page_size='', page_no=1):
        """
        获取所有任务的状态
        :param task_status: 可以是str或者list。如果为空，则查询所有存在status字段的记录。
        """

        fields = {'name': 1}
        fields.update({k: 1 for k in self.task_types.keys()})
        page_size = self.default_page_size if page_size == '' else page_size
        pages = self.db.page.find({}, fields).limit(page_size).skip(page_size * (page_no - 1))
        return pages
