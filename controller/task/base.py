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
import random
from functools import cmp_to_key
from datetime import datetime
import controller.errors as errors
from controller.base import BaseHandler


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

    # 通过数据锁机制对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
    # 1.tasks。同一page的同阶任务（如block_cut_proor对blocks而言）或高阶任务（如column_cut_proof/char_cut_proof对blocks而言）
    # 2.roles。数据专家角色对所有page的授权字段

    # data_auth_maps指的是共享字段的数据锁可以授权给哪些tasks和哪些roles，即数据锁授权配置表。
    # 在进入数据字段edit操作和保存时，需要检查数据锁资质，以这个表来判断。
    data_auth_maps = {
        'blocks': {
            'tasks': ['block_cut_proof', 'block_cut_review', 'column_cut_proof', 'column_cut_review',
                      'char_cut_proof', 'char_cut_review', 'text_proof_1', 'text_proof_2',
                      'text_proof_3', 'text_review', 'text_hard'],
            'roles': ['切分专家']
        },
        'columns': {
            'tasks': ['column_cut_proof', 'column_cut_review', 'char_cut_proof', 'char_cut_review',
                      'text_proof_1', 'text_proof_2', 'text_proof_3', 'text_review', 'text_hard'],
            'roles': ['切分专家']
        },
        'chars': {
            'tasks': ['char_cut_proof', 'char_cut_review', 'text_proof_1', 'text_proof_2', 'text_proof_3',
                      'text_review', 'text_hard'],
            'roles': ['切分专家']
        },
        'text': {
            'tasks': ['text_review', 'text_hard'],
            'roles': ['文字专家']
        },

    }

    # task_shared_data_fields指的任务拥有哪些共享字段。只有拥有共享字段的任务才涉及到数据锁机制。
    # 在任务领取、保存、提交、完成、退回等时，需要判断是否要检查数据锁时，以这个表来判断。
    task_shared_data_fields = {
        'block_cut_proof': 'blocks',
        'block_cut_review': 'blocks',
        'column_cut_proof': 'columns',
        'column_cut_review': 'columns',
        'char_cut_proof': 'chars',
        'char_cut_review': 'chars',
        'text_review': 'text',
        'text_hard': 'text',
    }

    @classmethod
    def get_shared_data_field(cls, task_type):
        """ 获取任务保护的共享字段 """
        return cls.task_shared_data_fields.get(task_type)

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
    def cut_task_names(cls):
        return {k: v for k, v in cls.task_types.items() if 'cut_' in k}

    @classmethod
    def text_task_names(cls):
        return {k: v for k, v in cls.task_types.items() if 'text_' in k}

    @classmethod
    def simple_fileds(cls, include=None):
        """ 去掉一些内容较长的字段，如果需要保留，可以通过include进行设置 """
        simple = ['name', 'width', 'height', 'tasks', 'lock']
        include = [] if not include else include
        return {prop: 1 for prop in set(simple + include)}

    def find_my_tasks(self, page_name):
        """ 检查page_name对应的page中，当前用户有哪些任务 """
        page = self.db.page.find_one({'name': page_name}, self.simple_fileds())
        tasks = []
        for k, task in page['tasks'].items():
            if task.get('picked_user_id') == self.current_user['_id']:
                tasks.append(k)
        return tasks

    def has_data_lock(self, page_name, data_field, is_temp=None):
        """ 检查page_name对应的page中，当前用户是否拥有data_field对应的数据 """
        condition = {'name': page_name, 'lock.%s.locked_user_id' % data_field: self.current_user['_id']}
        assert is_temp in [None, True, False]
        if is_temp is not None:
            condition.update({'is_temp': is_temp})
        n = self.db.page.count_documents(condition)
        return n > 0

    def is_data_locked(self, page_name, data_field):
        """检查page_name对应的page中，data_field对应的数据是否已经被锁定"""
        page = self.db.page.find({'name': page_name}, self.simple_fileds())
        return True if self.prop(page, 'lock.%s.locked_user_id' % data_field) else False

    def get_temp_data_lock(self, page_name, data_field):
        """ 将page_name对应的page中，data_field对应的数据锁分配给当前用户，成功时返回True，失败时返回errors.xxx。
            它提供给update或edit时，分配临时锁，不能获取长时锁（长时锁由系统在任务领取时分配，是任务提交时释放）。
        """

        def assign_lock(lock_type):
            """ lock_type指的是来自哪个任务或者哪个角色 """
            r = self.db.page.update_one({'name': page_name}, {'$set': {
                'lock.' + data_field: {
                    "is_temp": True,
                    "lock_type": lock_type,
                    "locked_by": self.current_user['name'],
                    "locked_user_id": self.current_user['_id'],
                    "locked_time": datetime.now(),
                }
            }})
            return r.matched_count > 0

        assert data_field in self.data_auth_maps

        if self.has_data_lock(page_name, data_field):
            return True

        # 检查是否有数据编辑对应的roles（有一个角色即可）
        roles = list(set(self.current_user['roles']) & set(self.data_auth_maps[data_field]['roles']))
        if roles:
            if not self.is_data_locked(page_name, data_field):
                return True if assign_lock(('roles', roles)) else errors.data_lock_failed
            else:
                return errors.data_is_locked

        # 检查是否有同一page的同阶或高阶tasks
        my_tasks = self.find_my_tasks(page_name)
        tasks = list(set(my_tasks) & set(self.data_auth_maps[data_field]['tasks']))
        if tasks:
            if not self.is_data_locked(page_name, data_field):
                return True if assign_lock(('tasks', tasks)) else errors.data_lock_failed
            else:
                return errors.data_is_locked

        return errors.data_unauthorized

    def release_temp_data_lock(self, page_name, data_field):
        """ 将page_name对应的page中，data_field对应的数据锁释放。 """
        if data_field and data_field in self.data_auth_maps and self.has_data_lock(page_name, data_field, is_temp=True):
            self.db.page.update_one({'name': page_name}, {'$set': {'lock.%s': {}}})

    def check_auth(self, mode, page, task_type):
        """ 检查任务权限以及数据锁 """
        if isinstance(page, str):
            page = self.db.page.find_one({'name': page})
        if not page:
            return False

        # do/update模式下，需要检查任务权限，直接抛出错误
        if mode in ['do', 'update']:
            render = '/api' not in self.request.path
            # 检查任务是否已分配给当前用户
            task_field = 'tasks.' + task_type
            if not self.current_user or self.prop(page, task_field + '.picked_user_id') != self.current_user['_id']:
                return self.send_error_response(errors.task_unauthorized, render=render, reason=page['name'])
            # 检查任务状态以及是否与mode匹配
            status = self.prop(page, task_field + '.status')
            if status not in [self.STATUS_PICKED, self.STATUS_FINISHED]:
                return self.send_error_response(errors.task_unauthorized, render=render, reason=page['name'])
            if status == self.STATUS_FINISHED and mode == 'do':
                return self.send_error_response(errors.task_finished_not_allowed_do, render=render, reason=page['name'])

        # do/update/edit模式下，需要检查数据锁（在配置表中申明的字段才进行检查）
        auth = False
        if mode in ['do', 'update', 'edit']:
            data_field = self.get_shared_data_field(task_type)
            if not data_field or data_field not in self.data_auth_maps:  # 无共享字段或共享字段没有在授权表中
                auth = True
            elif (self.has_data_lock(page['name'], data_field)
                  or self.get_temp_data_lock(page['name'], data_field) is True):
                auth = True

        return auth

    def update_post_tasks(self, page_name, task_type):
        """ 任务完成的时候，更新后置任务的状态 """

        def find_post_tasks():
            post_tasks = []
            for k, task in page.get('tasks').items():
                if task_type in (task.get('pre_tasks') or []):
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

    def get_my_tasks_by_type(self, task_type, status=None, name=None, order=None, page_size=0, page_no=1):
        """获取我的任务/任务列表"""
        if task_type not in self.all_types():
            return [], 0

        assert status is None or status in [self.STATUS_PICKED, self.STATUS_FINISHED]

        status = [self.STATUS_PICKED, self.STATUS_FINISHED] if not status else [status]
        if task_type == 'text_proof':
            condition = {
                '$or': [{
                    'tasks.text_proof_%s.picked_user_id' % i: self.current_user['_id'],
                    'tasks.text_proof_%s.status' % i: {"$in": status},
                } for i in [1, 2, 3]]
            }
        else:
            condition = {
                'tasks.%s.picked_user_id' % task_type: self.current_user['_id'],
                'tasks.%s.status' % task_type: {"$in": status},
            }

        if name:
            condition['name'] = {'$regex': '.*%s.*' % name}

        query = self.db.page.find(condition, self.simple_fileds())
        total_count = self.db.page.count_documents(condition)

        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort("tasks.%s.%s" % (task_type, order), asc)

        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count

    def select_my_text_proof(self, page):
        """从一个page中，选择我的文字校对任务"""
        for i in range(1, 4):
            if self.prop(page, 'tasks.text_proof_%s.picked_user_id' % i) == self.current_user['_id']:
                return 'text_proof_%s' % i

    def get_lobby_tasks_by_type(self, task_type, page_size=0):
        """按优先级排序后随机获取任务大厅/任务列表"""

        def get_priority(page):
            t = self.select_lobby_text_proof(page) if task_type == 'text_proof' else task_type
            priority = self.prop(page, 'tasks.%s.priority' % t) or 0
            return priority

        if task_type not in self.all_types():
            return [], 0
        if task_type == 'text_proof':
            condition = {'$or': [{'tasks.text_proof_%s.status' % i: self.STATUS_OPENED} for i in [1, 2, 3]]}
            condition.update(
                {'tasks.text_proof_%s.picked_user_id' % i: {'$ne': self.current_user['_id']} for i in [1, 2, 3]}
            )
        else:
            condition = {'tasks.%s.status' % task_type: self.STATUS_OPENED}
        total_count = self.db.page.count_documents(condition)
        pages = list(self.db.page.find(condition, self.simple_fileds()).limit(self.MAX_RECORDS))
        random.shuffle(pages)
        pages.sort(key=cmp_to_key(lambda a, b: get_priority(a) - get_priority(b)), reverse=True)
        page_size = page_size or self.config['pager']['page_size']
        return pages[:page_size], total_count

    def select_lobby_text_proof(self, page):
        """从一个page中，选择已发布且优先级最高的文字校对任务"""
        text_proof, priority = '', -1
        for i in range(1, 4):
            s = self.prop(page, 'tasks.text_proof_%s.status' % i)
            p = self.prop(page, 'tasks.text_proof_%s.priority' % i) or 0
            if s == self.STATUS_OPENED and p > priority:
                text_proof, priority = 'text_proof_%s' % i, p
        return text_proof

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
            query.sort("tasks.%s.%s" % (task_type, order), asc)

        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count
