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
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、页面集合（page_name）
@time: 2019/3/11
"""

import re
from datetime import datetime
import controller.errors as errors
from controller.base import BaseHandler
from controller.role import url_placeholder as holder


class TaskHandler(BaseHandler):
    # 任务类型表
    task_types = {
        'block_cut_proof': '切栏校对',
        'block_cut_review': '切栏审定',
        'column_cut_proof': '切列校对',
        'column_cut_review': '切列审定',
        'char_cut_proof': '切字校对',
        'char_cut_review': '切字审定',
        'text_proof_1': '文字校一',
        'text_proof_2': '文字校二',
        'text_proof_3': '文字校三',
        'text_review': '文字审定',
        'text_hard': '难字处理',
    }

    # 任务状态表
    STATUS_UNREADY = 'unready'
    STATUS_READY = 'ready'
    STATUS_OPENED = 'opened'
    STATUS_PENDING = 'pending'
    STATUS_PICKED = 'picked'
    STATUS_RETURNED = 'returned'
    STATUS_FINISHED = 'finished'
    status_names = {
        STATUS_UNREADY: '数据未就绪',
        STATUS_READY: '数据已就绪',
        STATUS_OPENED: '已发布未领取',
        STATUS_PENDING: '等待前置任务',
        STATUS_PICKED: '进行中',
        STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }

    prior_names = {3: '高', 2: '中', 1: '低'}

    MAX_RECORDS = 10000

    # 数据锁授权机制。以下两种情况可以分配数据锁：
    # 1.tasks。
    #   同一page的同阶任务（如block_cut_proor对blocks而言），通过'/task/do/@task_type/@page_name'的方式修改数据。
    #   同一page的高阶任务（如column_cut_proof/char_cut_proof对blocks而言），通过'/task/edit/@task_type/@page_name'的方式修改数据。
    # 2.roles。
    #   专家角色对所拥有的数据有修改权限，通过'/task/edit/@task_type/@page_name'的方式修改数据。
    data_lock_maps = {
        'blocks': {
            'tasks': [
                'block_cut_proof', 'block_cut_review',
                'column_cut_proof', 'column_cut_review',
                'char_cut_proof', 'char_cut_review',
                'text_proof_1', 'text_proof_2', 'text_proof_3',
                'text_review', 'text_hard',
            ],
            'roles': ['切分专家']
        },
        'columns': {
            'tasks': [
                'column_cut_proof', 'column_cut_review',
                'char_cut_proof', 'char_cut_review',
                'text_proof_1', 'text_proof_2', 'text_proof_3',
                'text_review', 'text_hard',
            ],
            'roles': ['切分专家']
        },
        'chars': {
            'tasks': [
                'char_cut_proof', 'char_cut_review',
                'text_proof_1', 'text_proof_2', 'text_proof_3',
                'text_review', 'text_hard',
            ],
            'roles': ['切分专家']
        },
        'text': {
            'tasks': [
                'text_review', 'text_hard',
            ],
            'roles': ['文字专家']
        },
        'ocr': {
            'roles': ['数据管理员']
        },
    }

    @classmethod
    def prop(cls, obj, key):
        for s in key.split('.'):
            obj = obj.get(s) if isinstance(obj, dict) else None
        return obj

    @classmethod
    def all_types(cls):
        all_types = {'text_proof': '文字校对'}
        all_types.update(cls.task_types)
        return all_types

    @classmethod
    def simple_fileds(cls):
        exclude = ['blocks', 'columns', 'chars', 'ocr', 'text']
        exclude += ['tasks.text_proof_%s.%s' % (i, typ) for i in [1, 2, 3] for typ in ['cmp', 'result']]
        return {prop: 0 for prop in exclude}

    @classmethod
    def get_data_type(cls, task_type):
        """根据task_type获取data_type"""
        data_type_maps = {
            'block_cut_proof': 'blocks',
            'block_cut_review': 'blocks',
            'column_cut_proof': 'columns',
            'column_cut_review': 'columns',
            'char_cut_proof': 'chars',
            'char_cut_review': 'chars',
            'text_review': 'text',
            'text_hard': 'text',
        }
        return data_type_maps.get(task_type)

    @classmethod
    def cut_task_names(cls):
        return {k: v for k, v in cls.task_types.items() if 'cut_' in k}

    @classmethod
    def text_task_names(cls):
        return {k: v for k, v in cls.task_types.items() if 'text_' in k}

    def prepare(self):
        super(TaskHandler, self).prepare()

        # 针对'/task/do'的请求，检查本任务是否已分配给当前用户（在领取任务的时候已分配数据权限，因此不必检查数据权限）
        match = re.match(r'.*/task/do/(%s)/(%s)' % (holder['task_type'], holder['page_name']), self.request.path)
        if match:
            task_type, page_name = match.group(1), match.group(2)
            if not self.is_my_task(page_name, task_type):   #
                return self.send_error_response(errors.unauthorized)

        # 针对'/task/edit'的get/post请求
        match = re.match(r'.*/task/edit/(%s)/(%s)' % (holder['data_type'], holder['page_name']), self.request.path)
        if match:
            if self.request.method == 'GET':    # 针对GET请求，将数据锁分配给当前用户
                data_type, page_name = match.group(1), match.group(2)
                return self.get_data_lock(page_name, data_type)

            if self.request.method == 'POST':   # 针对POST请求，检查数据锁是否已分配给当前用户
                data_type, page_name = match.group(1), match.group(2)
                if not self.has_data_lock(page_name, data_type):
                    return self.send_error_response(errors.data_unauthorized)

    def is_my_task(self, page_name, task_type):
        """检查page_name对应的page中，task_type对应的任务是否分配给当前用户"""
        n = self.db.page.count_documents({
            'name': page_name, 'tasks.%s.picked_user_id' % task_type: self.current_user['_id']
        })
        return n > 0

    def find_my_tasks(self, page_name):
        """检查page_name对应的page中，当前用户有哪些任务"""
        page = self.db.page.find_one({'name': page_name}, self.simple_fileds())
        tasks = []
        for k, task in page['tasks'].items():
            if task.get('picked_by') == self.current_user['_id']:
                tasks.append(k)
        return tasks
    
    def has_data_lock(self, page_name, data_type):
        """检查page_name对应的page中，当前用户是否拥有data_type对应的数据"""
        n = self.db.page.count_documents({
            'name': page_name, 'lock.%s.locked_user_id' % data_type: self.current_user['_id']
        })
        return True if n > 0 else False

    def is_data_locked(self, page_name, data_type):
        """检查page_name对应的page中，data_type对应的数据是否已经被锁定"""
        page = self.db.page.find({'name': page_name}, self.simple_fileds())
        if page and self.prop(page, 'lock.%s.locked_user_id' % data_type):
            return True
        return False

    def get_data_lock(self, page_name, data_type):
        """将page_name对应的page中，data_type对应的数据锁分配给当前用户"""
        def assign_lock(lock_type):
            # lock_type指的是来自哪个任务或者哪个角色
            r = self.db.user.update_one({'name': page_name}, {'$set': {
                'lock.' + data_type: {
                    "lock_type": lock_type,
                    "locked_by": self.current_user['name'],
                    "locked_user_id": self.current_user['_id'],
                    "locked_time": datetime.now()
                }
            }})
            return True if r.matched_count > 0 else False

        assert data_type in self.data_lock_maps

        if self.has_data_lock(page_name, data_type):
            return True

        # 检查是否有数据编辑对应的roles（有一个角色即可）
        roles = set(self.current_user['roles']) & set(self.data_lock_maps[data_type]['roles'])
        if roles:
            if not self.is_data_locked(page_name, data_type):
                return True if assign_lock(('roles', roles)) else self.send_error_response(errors.data_lock_failed)
            else:
                return self.send_error_response(errors.data_is_locked)
        # 检查是否有同一page的同阶或高阶tasks
        my_tasks = self.find_my_tasks(page_name)
        tasks = set(my_tasks) & set(self.data_lock_maps[data_type]['tasks'])
        if tasks:
            if not self.is_data_locked(page_name, data_type):
                return True if assign_lock(('tasks', tasks)) else self.send_error_response(errors.data_lock_failed)
            else:
                return self.send_error_response(errors.data_is_locked)

        return self.send_error_response(errors.data_lock_failed)

    def release_data_lock(self, page_name, data_type):
        """ 将page_name对应的page中，data_type对应的数据锁释放
        :param data_type 如果data_type为task_type类型，则计算其data_type
        """
        page_name, data_type = page_name.strip(), data_type.strip()
        if data_type in self.task_types:
            data_type = self.get_data_type(data_type)

        if data_type and data_type in self.data_lock_maps and self.has_data_lock(page_name, data_type):
            self.db.page.update_one({'name': page_name}, {'$set': {'lock.%s': None}})

    def update_post_tasks(self, page_name, task_type):
        """page_name对应的task_type任务完成的时候，更新后置任务的状态"""
        def find_post_tasks():
            post_tasks = []
            for k, task in page.get('tasks'):
                if task_type in task.get('pre_tasks'):
                    post_tasks.append(k)
            return post_tasks

        def pre_tasks_all_finished(task):
            pre_tasks = self.prop(page, 'tasks.%s.pre_tasks' % task)
            for pre_task in pre_tasks:
                if self.STATUS_FINISHED != self.prop(page, 'tasks.%s.status' % pre_task):
                    return False
            return True

        page = self.db.page.find_one({
            'name': page_name,
            'tasks.%s.picked_user_id' % task_type: self.current_user['_id'],
            'tasks.%s.status' % task_type: self.STATUS_FINISHED,
        })
        if page:
            update = {}
            for t in find_post_tasks():
                if self.prop(page, 'tasks.%s.status' % t) == self.STATUS_PENDING and pre_tasks_all_finished(t):
                    update.update({'tasks.%s.status' % t: self.STATUS_OPENED})
            if update:
                self.db.page.update_one({'name': page_name}, {'$set': update})

    def get_tasks_by_type(self, task_type, type_status=None, name=None, order=None, page_size=0, page_no=1):
        """获取任务管理/任务列表"""
        if task_type and task_type not in self.task_types.keys():
            return [], 0

        condition = dict()
        if task_type and type_status:
            condition['tasks.%s.status' % task_type] = type_status
        if name:
            condition['name'] = {'$regex': '.*%s.*' % name}

        query = self.db.page.find(condition, self.simple_fileds())
        total_count = query.count()

        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort("%s.%s" % (task_type, order), asc)

        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count
