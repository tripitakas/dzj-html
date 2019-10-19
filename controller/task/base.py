#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler基类
@time: 2019/3/11
"""
from .conf import TaskConfig
from datetime import datetime
import controller.auth as auth
import controller.errors as errors
from controller.base import BaseHandler


class TaskHandler(BaseHandler, TaskConfig):
    # 任务状态表
    STATUS_OPENED = 'opened'
    STATUS_PENDING = 'pending'
    STATUS_PICKED = 'picked'
    STATUS_RETURNED = 'returned'
    STATUS_RETRIEVED = 'retrieved'
    STATUS_FINISHED = 'finished'
    task_status_names = {
        STATUS_OPENED: '已发布未领取', STATUS_PENDING: '等待前置任务', STATUS_PICKED: '进行中',
        STATUS_RETURNED: '已退回', STATUS_RETRIEVED: '已回收', STATUS_FINISHED: '已完成',
    }

    # 数据状态表
    STATUS_UNREADY = 'unready'
    STATUS_TODO = 'todo'
    STATUS_READY = 'ready'
    data_status_names = {STATUS_UNREADY: '未就绪', STATUS_TODO: '待办', STATUS_READY: '已就绪'}

    # 任务优先级
    prior_names = {3: '高', 2: '中', 1: '低'}

    def find_tasks(self, task_type, doc_id=None, status=None, size=None, mine=False):
        assert task_type in self.task_types
        collection, id_name = self.get_task_meta(task_type)[:2]
        condition = dict(task_type=task_type, collection=collection, id_name=id_name)
        if doc_id:
            condition.update({'doc_id': doc_id if isinstance(doc_id, str) else {'$in': doc_id}})
        if status:
            condition.update({'status': status if isinstance(status, str) else {'$in': status}})
        if mine:
            condition.update({'picked_user_id': self.current_user['_id']})
        tasks = self.db.task.find(condition)
        if size:
            tasks.limit(size)
        return list(tasks)

    def check_task_auth(self, task, mode):
        """ 检查当前用户是否拥有相应的任务权限 """
        assert task['task_type'] in self.task_types
        # 检查任务权限
        reason = '%s@%s' % (task['task_type'], task['doc_id'])
        render = '/api' not in self.request.path and not self.get_query_argument('_raw', 0)
        if mode in ['do', 'update']:
            if task['picked_user_id'] != self.current_user.get('_id'):
                return self.send_error_response(errors.task_unauthorized, render=render, reason=reason)
            if mode == 'do' and task['status'] != self.STATUS_PICKED:
                return self.send_error_response(errors.task_can_only_do_picked, render=render, reason=reason)
            if mode == 'update' and task['status'] != self.STATUS_FINISHED:
                return self.send_error_response(errors.task_can_only_update_finished, render=render, reason=reason)

    def check_task_lock(self, task, mode):
        """ 检查当前用户是否拥有相应的数据锁，成功时返回True，失败时返回错误代码 """
        if mode in ['do', 'update', 'edit']:
            shared_field = self.get_shared_field(task['task_type'])
            # 没有共享字段时，通过检查
            if not shared_field or shared_field not in self.data_auth_maps:
                return True
            # 有共享字段时，能获取数据锁，也通过检查
            return self.get_data_lock(task['doc_id'], shared_field)
        else:
            return True

    def finish_task(self, task):
        """ 任务提交 """
        # 更新当前任务
        update = {'status': self.STATUS_FINISHED, 'finished_time': datetime.now()}
        self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        # 释放数据锁
        shared_field = self.get_shared_field(task['task_type'])
        if shared_field and shared_field in self.data_auth_maps:
            update['lock.' + shared_field] = {}
            self.db[task['collection']].update_one({task['id_name']: task['doc_id']}, {'$set': update})
        # 更新后置任务
        self.update_post_tasks(task)

    def update_post_tasks(self, task):
        """ 更新后置任务的状态 """
        task_type = task['task_type']
        condition = dict(collection=task['collection'], id_name=task['id_name'], doc_id=task['doc_id'])
        tasks = list(self.db.task.find(condition))
        finished = [t['task_type'] for t in tasks if t['status'] == self.STATUS_FINISHED] + [task_type]
        for t in tasks:
            pre_tasks = t.get('pre_tasks', {})
            # 检查任务t的所有前置任务的状态
            for pre_task in pre_tasks:
                if pre_task in finished:
                    pre_tasks[pre_task] = self.STATUS_FINISHED
            update = {'pre_tasks': pre_tasks}
            # 如果当前任务状态为悬挂，且所有前置任务均已完成，则设置状态为已发布
            unfinished = [v for v in pre_tasks.values() if v != self.STATUS_FINISHED]
            if t['status'] == self.STATUS_PENDING and not unfinished:
                update.update({'status': self.STATUS_OPENED})
            self.db.task.update_one({'_id': t['_id']}, {'$set': update})

    def has_data_lock(self, doc_id, shared_field, is_temp=None):
        """ 检查当前用户是否拥有某数据锁 """
        assert is_temp in [None, True, False]
        assert shared_field in self.data_auth_maps
        id_name = self.data_auth_maps[shared_field]['id']
        collection = self.data_auth_maps[shared_field]['collection']

        condition = {id_name: doc_id, 'lock.%s.locked_user_id' % shared_field: self.current_user['_id']}
        if is_temp is not None:
            condition.update({'lock.%s.is_temp' % shared_field: is_temp})
        n = self.db[collection].count_documents(condition)
        return n > 0

    def is_data_locked(self, doc_id, shared_field):
        """ 检查数据是否已经被锁定"""
        assert shared_field in self.data_auth_maps
        id_name = self.data_auth_maps[shared_field]['id']
        collection = self.data_auth_maps[shared_field]['collection']

        data = self.db[collection].find_one({id_name: doc_id})
        return True if self.prop(data, 'lock.%s.locked_user_id' % shared_field) else False

    def get_lock_qualification(self, doc_id, shared_field):
        """ 检查用户是否有数据锁资质并返回资质 """
        assert shared_field in self.data_auth_maps
        id_name = self.data_auth_maps[shared_field]['id']
        collection = self.data_auth_maps[shared_field]['collection']

        # 检查当前用户是否有数据锁对应的专家角色（有一个角色即可）
        user_all_roles = auth.get_all_roles(self.current_user['roles'])
        roles = list(set(user_all_roles) & set(self.data_auth_maps[shared_field]['roles']))
        if roles:
            return dict(roles=roles)

        # 检查当前用户是否有该数据的同阶或高阶任务
        tasks = self.db.task.find_one({'data': dict(collection=collection, id_name=id_name, doc_id=doc_id)})
        my_tasks = [t for t in tasks if t.get('picked_user_id') == self.current_user['_id']
                    and t.get('status') != self.STATUS_RETURNED]
        tasks = list(set(my_tasks) & set(self.data_auth_maps[shared_field]['tasks']))
        if tasks:
            return dict(tasks=tasks)

        return False

    def get_data_lock(self, doc_id, shared_field):
        """ 将临时数据锁分配给当前用户。成功时返回True，失败时返回错误代码 """

        def assign_lock(qualification):
            """ qualification指的是来自哪个任务或者哪个角色 """
            r = self.db[collection].update_one({id_name: doc_id}, {'$set': {
                'lock.' + shared_field: {
                    "is_temp": True,
                    "lock_type": qualification,
                    "locked_by": self.current_user['name'],
                    "locked_user_id": self.current_user['_id'],
                    "locked_time": datetime.now(),
                }
            }})
            return r.matched_count > 0

        assert shared_field in self.data_auth_maps
        id_name = self.data_auth_maps[shared_field]['id']
        collection = self.data_auth_maps[shared_field]['collection']

        if self.has_data_lock(doc_id, shared_field):
            return True

        if self.is_data_locked(doc_id, shared_field):
            return errors.data_is_locked

        qualification = self.get_lock_qualification(doc_id, shared_field)
        if qualification is False:
            return errors.unauthorized

        return True if assign_lock(qualification) else errors.data_lock_failed

    def release_data_lock(self, doc_id, shared_field=None, is_temp=True):
        """ 释放数据锁 """
        assert type(doc_id) in [str, list]
        assert shared_field in self.data_auth_maps
        id_name = self.data_auth_maps[shared_field]['id']
        collection = self.data_auth_maps[shared_field]['collection']

        if shared_field in self.data_auth_maps:
            if isinstance(doc_id, str):
                self.db[collection].update_one({id_name: doc_id}, {'$set': {'lock.%s' % shared_field: dict()}})
            else:
                condition = {id_name: {'$in': doc_id}, 'is_temp': is_temp}
                self.db[collection].update_many(condition, {'$set': {'lock.%s' % shared_field: dict()}})
