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
from datetime import datetime
import controller.role as role
from functools import cmp_to_key
import controller.errors as errors
from controller.base import BaseHandler


class TaskHandler(BaseHandler):
    # 任务类型定义表。
    # pre_tasks：默认的前置任务
    # steps：默认的子步骤
    # shared_data：该任务共享和保护的数据字段
    task_types = {
        'cut_proof': {'name': '切分校对', 'pre_tasks': None, 'steps': None, 'shared_data': 'page.chars'},
        'cut_review': {'name': '切分审定', 'pre_tasks': ['cut_proof'], 'steps': None, 'shared_data': 'page.chars'},
        'text_proof': {'name': '文字校对', 'pre_tasks': None, 'steps': None, 'shared_data': 'page.chars'},
        'text_review': {'name': '文字审定', 'pre_tasks': ['text_review'], 'steps': None, 'shared_data': 'page.chars'},
        'text_hard': {'name': '难字审定', 'pre_tasks': ['text_review'], 'steps': None, 'shared_data': 'page.chars'},
    }

    # 数据锁权限配置表。
    # 在update或edit操作时，需要检查数据锁资质，以这个表来判断。
    data_auth_maps = {
        'page.chars': {
            'tasks': ['cut_proof', 'cut_review', 'text_proof', 'text_review', 'text_hard'],
            'roles': ['切分专家']
        },
        'page.text': {
            'tasks': ['text_review', 'text_hard'],
            'roles': ['文字专家']
        },
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
        STATUS_UNREADY: '数据未就绪', STATUS_READY: '数据已就绪', STATUS_OPENED: '已发布未领取',
        STATUS_PENDING: '等待前置任务', STATUS_PICKED: '进行中',
        STATUS_RETURNED: '已退回', STATUS_FINISHED: '已完成',
    }

    prior_names = {3: '高', 2: '中', 1: '低'}

    MAX_RECORDS = 10000

    @classmethod
    def prop(cls, obj, key):
        for s in key.split('.'):
            obj = obj.get(s) if isinstance(obj, dict) else None
        return obj

    @classmethod
    def task_names(cls):
        return {k: v.get('name') for k, v in cls.task_types.items()}

    def check_auth(self, mode, page, task_type):
        """ 检查任务权限以及数据锁 """
        if isinstance(page, str):
            page = self.db.page.find_one({'name': page})
        if not page:
            return False

        # do/update模式下，需要检查任务权限，直接抛出错误
        if mode in ['do', 'update']:
            render = '/api' not in self.request.path and not self.get_query_argument('_raw', 0)
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
            data_field = self.get_shared_data(task_type)
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
        if task_type not in self.task_types:
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

        query = self.db.page.find(condition)
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

        if task_type not in self.task_types:
            return [], 0
        if task_type == 'text_proof':
            condition = {'$or': [{'tasks.text_proof_%s.status' % i: self.STATUS_OPENED} for i in [1, 2, 3]]}
            condition.update(
                {'tasks.text_proof_%s.picked_user_id' % i: {'$ne': self.current_user['_id']} for i in [1, 2, 3]}
            )
        else:
            condition = {'tasks.%s.status' % task_type: self.STATUS_OPENED}
        total_count = self.db.page.count_documents(condition)
        pages = list(self.db.page.find(condition).limit(self.MAX_RECORDS))
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

        query = self.db.page.find(condition)
        total_count = self.db.page.count_documents(condition)

        if order:
            order, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort("tasks.%s.%s" % (task_type, order), asc)

        page_size = page_size or self.config['pager']['page_size']
        page_no = page_no if page_no >= 1 else 1
        pages = query.skip(page_size * (page_no - 1)).limit(page_size)
        return list(pages), total_count

    """ 数据锁介绍
    1）数据锁的目的：通过数据锁对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
      1.tasks。同一page的同阶任务（如cut_proof对chars而言）或高阶任务（如text_proof对chars而言）
      2.roles。数据专家角色对所有page的授权字段
    2）数据锁的类型：
      1.长时数据锁，由系统在领取任务时自动分配，在提交或退回任务时自动释放；
      2.临时数据锁，用户自己提交任务后update数据或者高阶任务用户以及专家edit数据时，分配临时数据锁，在窗口离开时解锁，或定时自动回收。
    3）数据锁的使用：
      1.首先在task_shared_data_fields中注册需要共享的数据字段；
      2.然后在data_auth_maps中配置，授权给相关的tasks或者roles访问。
    """

    @classmethod
    def get_shared_data(cls, task_type):
        """ 获取任务保护的共享字段 """
        return cls.prop(cls.task_types, '%s.shared_data' % task_type)

    def has_data_lock(self, table, id_name, id_value, data_field, is_temp=None):
        """ 检查当前用户是否拥有某数据锁
        :param table 数据表，即mongodb的collection
        :param id_name 作为id的字段名称
        :param id_value 作为id的字段值
        :param data_field 检查哪个数据字段
        :param is_temp 是否为临时锁
         """
        assert is_temp in [None, True, False]
        condition = {id_name: id_value, 'lock.%s.locked_user_id' % data_field: self.current_user['_id']}
        if is_temp is not None:
            condition.update({'lock.%s.is_temp' % data_field: is_temp})
        n = self.db[table].count_documents(condition)
        return n > 0

    def is_data_locked(self, table, id_name, id_value, data_field):
        """检查数据是否已经被锁定"""
        page = self.db[table].find_one({id_name: id_value})
        return True if self.prop(page, 'lock.%s.locked_user_id' % data_field) else False

    def get_temp_data_lock(self, table, id_name, id_value, data_field):
        """ 将临时数据锁分配给当前用户。（长时数据锁由系统在任务领取时分配，是任务提交时释放）。
        :return 成功时返回True，失败时返回errors.xxx。

        """

        def assign_lock(lock_type):
            """ lock_type指的是来自哪个任务或者哪个角色 """
            r = self.db[table].update_one({id_name: id_value}, {'$set': {
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
        if self.has_data_lock(table, id_name, id_value, data_field):
            return True
        # 检查是否有数据锁对应的角色（有一个角色即可）
        user_all_roles = role.get_all_roles(self.current_user['roles'])
        roles = list(set(user_all_roles) & set(self.data_auth_maps[data_field]['roles']))
        if roles:
            if not self.is_data_locked(table, id_name, id_value, data_field):
                return True if assign_lock(dict(roles=roles)) else errors.data_lock_failed
            else:
                return errors.data_is_locked
        # 检查当前用户拥有该数据的哪些任务
        tasks = self.db.task.find_one({'data': dict(table=table, id_name=id_name, id_value=id_value)})
        my_tasks = [t for t in tasks if t.get('picked_user_id') == self.current_user['_id']
                    and t.get('status') != self.STATUS_RETURNED]
        # 检查当前用户是否有该数据的同阶或高阶任务
        tasks = list(set(my_tasks) & set(self.data_auth_maps[data_field]['tasks']))
        if tasks:
            if not self.is_data_locked(table, id_name, id_value, data_field):
                return True if assign_lock(dict(tasks=tasks)) else errors.data_lock_failed
            else:
                return errors.data_is_locked

        return errors.data_unauthorized

    def release_temp_data_lock(self, table, id_name, id_value, data_field):
        """ 释放临时数据锁 """
        if data_field in self.data_auth_maps and self.has_data_lock(table, id_name, id_value, data_field, is_temp=True):
            self.db[table].update_one({id_name: id_value}, {'$set': {'lock.%s' % data_field: dict()}})
