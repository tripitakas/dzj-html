#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler基类
    https://github.com/tripitakas/tripitaka-web/wiki/Task-Flow-Introduction
    1. 任务状态。
    任务数据未到位时，状态为“unready”。上传数据后，程序进行检查，如果满足发布条件，则状态置为“ready”。
    发布任务只能发布状态为“ready”的任务。如果没有前置任务，则直接发布，状态为“opened”；如果有前置任务，则悬挂，状态为“pending”。
    用户领取任务后，状态为“picked”，退回任务后，状态为“returned”，提交任务后，状态为“finished”。
    2. 前置任务
    任务配置表中定义了默认的前置任务。
    业务管理员在发布任务时，可以对前置任务进行修改，比如文字审定需要两次或者三次校对。发布任务后，任务的前置任务将记录在数据库中。
    如果任务包含前置任务，系统发布任务后，状态为“pending”。当前置任务状态都变为“finished”时，自动将当前任务发布为“opened”。
    3. 发布任务
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、页面集合（task_id）
@time: 2019/3/11
"""

from controller.base import BaseHandler
from functools import cmp_to_key
import random


class TaskHandler(BaseHandler):
    """
    任务类型配置表。
    @name 任务名称
    @pre_tasks 前置任务列表
    @sub_task_types 子任务列表
    """
    task_types = {
        'block_cut_proof': {'name': '切栏校对'},
        'block_cut_review': {'name': '切栏审定', 'pre_tasks': ['block_cut_proof']},
        'column_cut_proof': {'name': '切列校对'},
        'column_cut_review': {'name': '切列审定', 'pre_tasks': ['column_cut_proof']},
        'char_cut_proof': {'name': '切字校对'},
        'char_cut_review': {'name': '切字审定', 'pre_tasks': ['char_cut_proof']},
        'char_order_proof': {'name': '字序校对', 'pre_tasks': ['char_cut_review']},
        'char_order_review': {'name': '字序审定', 'pre_tasks': ['char_order_proof']},
        'text_proof': {'name': '文字校对', 'sub_task_types': {
            '1': {'name': '校一'},
            '2': {'name': '校二'},
            '3': {'name': '校三'},
        }},
        'text_review': {'name': '文字审定', 'pre_tasks': ['text_proof.1', 'text_proof.2', 'text_proof.3']},
        'text_hard': {'name': '难字处理', 'pre_tasks': ['text_review']},
    }

    # 任务状态表
    STATUS_UNREADY = 'unready'
    STATUS_READY = 'ready'
    STATUS_OPENED = 'opened'
    STATUS_PENDING = 'pending'
    STATUS_PICKED = 'picked'
    STATUS_RETURNED = 'returned'
    STATUS_FINISHED = 'finished'
    task_statuses = {
        STATUS_UNREADY: '数据未就绪',
        STATUS_READY: '数据已就绪',
        STATUS_OPENED: '已发布未领取',
        STATUS_PENDING: '等待前置任务',
        STATUS_PICKED: '进行中',
        STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }

    @property
    def flat_task_types(self):
        """ 将任务类型扁平化后，返回任务类型列表。 如果是二级任务，则表示为task_type.sub_task_type。"""
        types = []
        for k, v in self.task_types.items():
            if 'sub_task_types' not in v:
                types.append(k)
            else:
                types.extend(['%s.%s' % (k, t) for t in v['sub_task_types']])
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

    cut_task_names = {
        'block_cut_proof': '切栏校对',
        'block_cut_review': '切栏审定',
        'column_cut_proof': '切列校对',
        'column_cut_review': '切列审定',
        'char_cut_proof': '切字校对',
        'char_cut_review': '切字审定'
    }

    text_task_names = {
        'text_proof.1': '文字校一',
        'text_proof.2': '文字校二',
        'text_proof.3': '文字校三',
        'text_review': '文字审定'
    }

    @property
    def post_tasks(self):
        """ 后置任务类型 """
        post_types = {}
        for task_type, v in self.task_types.items():
            if 'pre_tasks' in v:
                post_types.update({t: task_type for t in v['pre_tasks']})
            elif 'sub_task_types' in v:
                for sub_type, sub_v in v['sub_task_types'].items():
                    if 'pre_tasks' in sub_v:
                        post_types.update({t: task_type + '.' + sub_type for t in sub_v['pre_tasks']})
        return post_types

    @property
    def pre_tasks(self):
        """ 前置任务类型 """

        def recursion(cur):
            """ 对于 pre_types[cur]，对其中每个任务类型再向该列表加入其上一级依赖的任务类型 """
            for k in pre_types.get(cur, [])[:]:
                pre_types[cur].extend(recursion(k))
            return pre_types.get(cur, [])

        pre_types = {}
        for task_type, v in self.task_types.items():
            if 'pre_tasks' in v:
                pre_types[task_type] = v['pre_tasks']
            elif 'sub_task_types' in v:
                for sub_type, sub_v in v['sub_task_types'].items():
                    if 'pre_tasks' in sub_v:
                        pre_types[task_type + '.' + sub_type] = v['pre_tasks']
        for task_type in pre_types:
            recursion(task_type)
        return pre_types

    def get_next_task_todo(self, task_type):
        """ 获取下一个代办任务。如果有未完成的任务，则优先分配。如果没有，则从任务大厅中自动分配。 """
        pass

    def get_tasks_info_by_type(self, task_type, task_status=None, page_size=0, page_no=1, more_conditions=None,
                               rand=False, sort=False):
        """
        获取指定类型、状态的任务列表
        :param task_type: 任务类型
        :param task_status: 任务状态，或多个任务状态的列表
        :param page_size: 分页大小
        :param page_no: 取第几页，首页为1
        :param more_conditions: 更多搜索条件
        :param rand: 任务随机排序
        :param sort: 随机且按优先级排序
        :return: 页面列表
        """

        def get_priority(page):
            return self.page_get_prop(page, task_type + '.priority') or '低'

        assert task_type in self.task_types.keys()
        assert not task_status or type(task_status) in [str, list]

        if not task_status and self.get_query_argument('status', None):
            task_status = self.get_query_argument('status')
        if type(task_status) == list:
            task_status = {"$in": task_status}

        if not task_status:  # task_status为空
            conditions = {}
        elif 'sub_task_types' in self.task_types[task_type]:  # 二级任务
            sub_types = self.task_types[task_type]['sub_task_types'].keys()
            conditions = {'$or': [{'%s.%s.status' % (task_type, t): task_status} for t in sub_types]}
        else:  # 一级任务
            conditions = {'%s.status' % task_type: task_status}

        more_conditions and conditions.update(more_conditions)

        fields = {'name': 1, task_type: 1}
        page_size = page_size or self.config['pager']['page_size']
        pages = self.db.page.find(conditions, fields)
        if rand:
            pages = list(pages)
            random.shuffle(pages)
            if sort:
                pages.sort(key=cmp_to_key(
                    lambda a, b: '高中低'.index(get_priority(a)) - '高中低'.index(get_priority(b))))
            return pages[:page_size]

        pages = pages.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages)

    @staticmethod
    def page_get_prop(page, name):
        obj = page
        for s in name.split('.'):
            obj = obj and obj.get(s)
        return obj

    def get_my_tasks_by_type(self, task_type, page_size='', page_no=1):
        """ 获取我的任务列表 """
        assert task_type in self.task_types

        user_id = self.current_user['_id']

        if 'sub_task_types' in self.task_types.get(task_type, {}):
            sub_types = self.task_types[task_type]['sub_task_types'].keys()
            conditions = {'$or': [{'%s.%s.picked_by' % (task_type, t): user_id} for t in sub_types]}
        else:
            conditions = {'%s.picked_by' % task_type: user_id}

        fields = {'name': 1, task_type: 1}
        page_size = page_size or self.config['pager']['page_size']
        pages = self.db.page.find(conditions, fields).skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages)

    def get_tasks_info(self, page_size='', page_no=1):
        """
        获取所有任务的状态
        :param task_status: 可以是str或者list。如果为空，则查询所有存在status字段的记录。
        """
        query = {}
        if self.get_query_argument('status', None) and self.get_query_argument('t', None):
            query[self.get_query_argument('t') + '.status'] = self.get_query_argument('status')
        fields = {'name': 1}
        fields.update({k: 1 for k in self.task_types.keys()})
        page_size = page_size or self.config['pager']['page_size']
        pages = self.db.page.find(query, fields).limit(page_size).skip(page_size * (page_no - 1))
        return list(pages)
