#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler。
一、任务模式
1. do。用户领取任务后，进入do模式。在do模式下，用户提交任务，系统将自动分配下一个任务
2. update。用户完成任务后，可以通过update模式进行修改
3. view。非任务所有者可以通过view模式来查看任务
4. browse。管理员可以通过browse模式来逐条浏览任务
二、 任务url
eg, @mode/@task_type/5e3139c6a197150011d65e9d
mode代表任务模式，view模式时，mode为空串
@time: 2019/10/16
"""
import re
from bson.objectid import ObjectId
from datetime import datetime
from controller import errors as e
from controller.task.task import Task
from controller.task.lock import Lock
from controller.base import BaseHandler


class TaskHandler(BaseHandler, Task, Lock):
    def __init__(self, application, request, **kwargs):
        super(TaskHandler, self).__init__(application, request, **kwargs)
        self.task = self.task_type = self.task_id = self.mode = self.steps = None
        self.has_lock = self.readonly = self.message = None

    def prepare(self):
        super().prepare()
        if self.error:
            return
        self.task = {}
        self.has_lock = False
        self.mode = self.get_task_mode()
        self.task_type = self.get_task_type()
        self.task_id = self.get_task_id()
        if self.task_id:
            # 检查任务是否存在
            self.task, self.error = self.get_task(self.task_id)
            if not self.task:
                return self.send_error_response(self.error)
            # 检查任务权限
            has_auth, self.error = self.check_task_auth(self.task)
            if not has_auth:
                return self.send_error_response(self.error)
            # 检查数据锁
            self.has_lock, self.error = self.check_data_lock(self.task)
            self.message = '' if self.has_lock else str(self.error[1])
            # 针对没有数据锁的情况，如果是提交修改则报错，否则不报错
            if not self.has_lock and '/api' in self.request.path and self.mode in ['do', 'update', 'edit']:
                return self.send_error_response(self.error)
            else:
                self.error = None
        self.steps = self.init_steps(self.task, self.task_type)
        self.readonly = not self.has_lock or self.mode in ['view', 'browse']

    def get_task(self, task_id):
        task = self.db.task.find_one({'_id': ObjectId(task_id)})
        error = e.task_not_existed if not task else None
        return task, error

    def find_many(self, task_type=None, status=None, size=None, order=None):
        """ 查找任务 """
        condition = dict()
        if task_type:
            condition.update({'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type})
        if status:
            condition.update({'status': status if isinstance(status, str) else {'$in': status}})
        query = self.db.task.find(condition)
        if size:
            query.limit(size)
        if order:
            o, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(o, asc)
        return list(query)

    def find_mine(self, task_type=None, page_size=None, order=None, status=None):
        """ 查找我的任务"""
        assert status in [None, self.STATUS_PICKED, self.STATUS_FINISHED]
        condition = {'picked_user_id': self.current_user['_id']}
        if task_type:
            condition.update({'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type})
        if status:
            condition.update({'status': status})
        else:
            condition.update({'status': {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]}})
        query = self.db.task.find(condition)
        if page_size:
            query.limit(page_size)
        if order:
            o, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(o, asc)
        return list(query)

    def count_task(self, task_type=None, status=None, mine=False):
        """ 统计任务数量"""
        condition = dict()
        if task_type:
            condition.update({'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type})
        if status:
            condition.update({'status': {'$in': [status] if isinstance(status, str) else status}})
        if mine:
            con_status = condition.get('status') or {}
            con_status.update({'$ne': self.STATUS_RETURNED})
            condition.update({'status': con_status})
            condition.update({'picked_user_id': self.current_user['_id']})
        return self.db.task.count_documents(condition)

    def get_task_mode(self):
        return (re.findall('(do|update|edit|browse)/', self.request.path) or ['view'])[0]

    def get_task_type(self):
        s = re.search(r'(^|do|update|browse)/([^/]+?)/([0-9a-z]{24})', self.request.path)
        return s.group(2) if s else ''

    def get_task_id(self):
        s = re.search(r'/([0-9a-z]{24})', self.request.path)
        return s.group(1) if s else ''

    def get_publish_meta(self, task_type):
        now = datetime.now()
        collection, id_name = self.get_data_conf(task_type)[:2]
        return dict(
            task_type=task_type, batch='', collection=collection, id_name=id_name, doc_id='',
            status='', priority='', steps={}, pre_tasks=[], input=None, result={},
            create_time=now, updated_time=now, publish_time=now,
            publish_user_id=self.current_user['_id'],
            publish_by=self.current_user['name']
        )

    def init_steps(self, task, task_type=None):
        """ 检查当前任务的步骤，缺省时自动填充默认设置，有误时报错"""
        steps = dict()
        current_step = self.get_query_argument('step', '')
        todo = self.prop(task, 'steps.todo') or self.get_steps(task_type) or ['']
        submitted = self.prop(task, 'steps.submitted') or ['']
        un_submitted = [s for s in todo if s not in submitted]
        if not current_step:
            current_step = un_submitted[0] if self.mode == 'do' else todo[0]
        elif current_step and current_step not in todo:
            current_step = todo[0]
        index = todo.index(current_step)
        steps['current'] = current_step
        steps['is_first'] = index == 0
        steps['is_last'] = index == len(todo) - 1
        steps['prev'] = todo[index - 1] if index > 0 else None
        steps['next'] = todo[index + 1] if index < len(todo) - 1 else None
        return steps

    def finish_task(self, task):
        """ 完成任务 """
        # 更新当前任务
        update = {'status': self.STATUS_FINISHED, 'finished_time': datetime.now()}
        self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        self.release_task_lock(task, self.current_user, update_level=True)
        self.update_doc(task, self.STATUS_FINISHED)
        self.add_op_log('finish_%s' % task['task_type'], target_id=task['_id'])
        # 更新后置任务
        condition = dict(collection=task['collection'], id_name=task['id_name'], doc_id=task['doc_id'])
        tasks = list(self.db.task.find(condition))
        finished_types = [t['task_type'] for t in tasks if t['status'] == self.STATUS_FINISHED]
        for _task in tasks:
            # 检查任务task的所有pre_tasks的状态
            pre_tasks = self.prop(_task, 'pre_tasks', {})
            pre_tasks.update({p: self.STATUS_FINISHED for p in pre_tasks if p in finished_types})
            update = {'pre_tasks': pre_tasks}
            # 如果当前任务为悬挂，且所有前置任务均已完成，则修改状态为已发布
            unfinished = [v for v in pre_tasks.values() if v != self.STATUS_FINISHED]
            if _task['status'] == self.STATUS_PENDING and not unfinished:
                update.update({'status': self.STATUS_PUBLISHED})
                self.update_doc(_task, self.STATUS_PUBLISHED)
            self.db.task.update_one({'_id': _task['_id']}, {'$set': update})

    def update_doc(self, task, status=None):
        """ 更新任务所关联的数据"""
        if task['doc_id']:
            collection, id_name = self.get_data_conf(task['task_type'])[:2]
            condition = {id_name: task['doc_id']}
            if status:
                self.db[collection].update_one(condition, {'$set': {'tasks.' + task['task_type']: status}})
            else:
                self.db[collection].update_one(condition, {'$unset': {'tasks.' + task['task_type']: ''}})

    def update_docs(self, doc_ids, task_type, status):
        """ 更新数据的任务状态"""
        collection, id_name = self.get_data_conf(task_type)[:2]
        self.db[collection].update_many({id_name: {'$in': list(doc_ids)}}, {'$set': {'tasks.' + task_type: status}})

    def check_task_auth(self, task, mode=None):
        """ 检查当前用户是否拥有相应的任务权限"""
        mode = self.get_task_mode() if not mode else mode
        error = (None, '')
        if mode in ['do', 'update']:
            if task.get('picked_user_id') != self.current_user.get('_id'):
                error = e.task_unauthorized_locked
            elif mode == 'do' and task['status'] != self.STATUS_PICKED:
                error = e.task_can_only_do_picked
            elif mode == 'update' and task['status'] != self.STATUS_FINISHED:
                error = e.task_can_only_update_finished
        has_auth = error[0] is None
        return has_auth, error

    def check_data_lock(self, task=None, doc_id=None, shared_field=None, mode=None):
        """ 检查当前用户是否拥有相应的数据锁"""
        if task:
            doc_id, shared_field = task['doc_id'], self.get_shared_field(task['task_type'])
        mode = self.get_task_mode() if not mode else mode
        has_lock, error = False, (None, '')
        if shared_field and mode == 'do':
            lock = self.get_data_lock_and_level(doc_id, shared_field)[0]
            if lock:
                has_lock = self.current_user['_id'] == self.prop(lock, 'locked_user_id')
                error = e.data_is_locked
        if shared_field and mode in ['update', 'edit']:
            r = self.assign_temp_lock(self.current_user, doc_id, shared_field)
            has_lock = r is True
            error = (None, '') if has_lock else r
        return has_lock, error
