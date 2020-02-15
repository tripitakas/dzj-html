#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler
一、mode 任务模式
1. do，做任务：用户做任务时，进入该模式
2. update，更新任务：用户完成任务后，可以通过update模式进行修改
3. view，查看任务：非任务所有者可以通过view模式来查看任务
4. browse，浏览任务：管理员可以通过browse模式来逐条浏览任务
5. edit，修改数据：专家用户修改数据使用
5. None，非任务、非数据修改请求
二、 url
1. do/update/browse，如：/task/(do/update/browse)/@task_type/5e3139c6a197150011d65e9d
2. edit，如：/data/cut_edit/@page_name，task_type为cut_edit，伪任务类型
3. view，如：/task/@task_type/5e3139c6a197150011d65e9d
4. 非任务、非数据修改请求，如/task/admin/page

@time: 2019/10/16
"""
import re
import random
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.task import Task
from controller.task.lock import Lock
from controller.base import BaseHandler


class TaskHandler(BaseHandler, Task, Lock):
    def __init__(self, application, request, **kwargs):
        """ 参数说明
        :param readonly: 是否只读。view/browse模式为只读
        :param has_lock: 是否有数据锁。详见controller.task.lock
        :param mode: 包括do/update/view/browse/edit或空等几种模式
        """
        super(TaskHandler, self).__init__(application, request, **kwargs)
        self.task_type = self.task_id = self.doc_id = self.message = ''
        self.mode = self.has_lock = self.readonly = None
        self.task = self.steps = self.doc = {}

    def prepare(self):
        """
        根据task_id参数，检查任务是否存在并设置任务，检查任务权限，设置任务相关参数
        根据doc_id/task_type参数，检查数据是否存在并设置数据，检查数据锁以及数据等级
        如果非任务的url请求需要使用该handler，则需要重载get_doc_id/get_task_type函数
        """
        super().prepare()
        self.mode = self.get_task_mode()
        self.task_id = self.get_task_id()
        # 检查任务
        if self.task_id:
            # 任务是否存在
            self.task, self.error = self.get_task(self.task_id)
            if not self.task:
                return self.send_error_response(self.error)
            self.task_id = str(self.task['_id'])
            # do和update模式下，检查任务权限
            if self.mode in ['do', 'update']:
                has_auth, self.error = self.check_task_auth(self.task)
                if not has_auth:
                    link = ('只读查看', re.sub('(do|update|edit)/', 'view/', self.request.full_url()))
                    return self.send_error_response(self.error, links=[link])
        # 检查数据
        self.doc_id = self.task.get('doc_id') or self.get_doc_id()
        self.task_type = self.task.get('task_type') or self.get_task_type()
        if self.doc_id and self.task_type:
            collection, id_name = self.get_data_conf(self.task_type)[:2]
            # 检查数据是否存在
            assert collection
            self.doc = self.db[collection].find_one({id_name: self.doc_id})
            if not self.doc:
                return self.send_error_response(e.no_object, message='数据%s不存在' % self.doc_id)
            # do/update/edit模式下，检查数据锁
            if self.mode in ['do', 'update', 'edit']:
                self.has_lock, error = self.check_my_lock()
                if self.has_lock is False:
                    if '/data/cut_edit/' in self.request.path:
                        return self.redirect(self.request.full_url().replace('cut_edit', 'cut_view'))
                    return self.send_error_response(error)
        # 设置其它参数
        self.steps = self.init_steps(self.task, self.task_type)
        self.readonly = self.mode in ['view', 'browse', '']

    def get_task(self, task_id):
        """ 根据task_id/to以及相关条件查找任务"""
        # 查找当前任务
        task = self.db.task.find_one({'_id': ObjectId(task_id)})
        if not task:
            return None, (e.task_not_existed[0], '没有找到任务%s' % task_id)
        to = self.get_query_argument('to', '')
        if not to:
            return task, None
        # 查找目标任务。to为prev时，查找前一个任务，即_id比task_id大的任务
        condition = self.get_task_search_condition(self.request.query)[0]
        condition.update({'_id': {'$gt' if to == 'prev' else '$lt': ObjectId(task_id)}})
        to_task = self.db.task.find_one(condition, sort=[('_id', 1 if to == 'prev' else -1)])
        if not to_task:
            error = e.task_not_existed[0], '没有找到任务%s的%s任务' % (task_id, '前一个' if to == 'prev' else '后一个')
            return None, error
        elif task['task_type'] != to_task['task_type']:
            # 如果task和to_task任务类型不一致，则切换url
            query = re.sub('[?&]to=(prev|next)', '', self.request.query)
            url = '/task/browse/%s/%s?' % (to_task['task_type'], to_task['_id']) + query
            self.redirect(url.rstrip('?'))
            return None, e.task_type_error
        return to_task, None

    def get_task_id(self):
        s = re.search(r'/([0-9a-z]{24})(\?|$|\/)', self.request.path)
        return s.group(1) if s else ''

    def get_doc_id(self):
        """ 获取数据id。子类可重载，以便prepare函数调用"""
        s = re.search(r'/([a-zA-Z]{2}(_\d+)+)(\?|$|\/)', self.request.path)
        return s.group(1) if s else ''

    def get_task_type(self):
        """ 获取任务类型。子类可重载，以便prepare函数调用"""
        # eg. /task/do/cut_proof/5e3139c6a197150011d65e9d
        s = re.search(r'/task/(do|update|browse)/([^/]+?)/([0-9a-z]{24})', self.request.path)
        task_type = s.group(2) if s else ''
        if not task_type:
            # eg. /data/cut_edit/@page_name
            s = re.search(r'/data/([a-z_]+_(edit|view))/([a-zA-Z]{2}(_\d+)+)(\?|$|\/)', self.request.path)
            task_type = s.group(1) if s else ''
        return task_type

    def get_task_mode(self):
        r = re.findall('(do|update|edit|browse)/', self.request.path)
        mode = r[0] if r else ''
        if not mode and self.get_task_id():
            mode = 'view'
        return mode

    def task_name(self):
        return self.get_task_name(self.task_type) or self.task_type

    def step_name(self):
        return self.get_step_name(self.steps.get('current')) or ''

    def find_many(self, task_type=None, status=None, size=None, order=None):
        """ 查找任务"""
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

    def find_mine(self, task_type=None, page_size=None, order=None, status=None, user_id=None):
        """ 查找我的任务"""
        assert status in [None, self.STATUS_PICKED, self.STATUS_FINISHED]
        user_id = user_id if user_id else self.user_id
        condition = {'picked_user_id': user_id}
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

    def find_lobby(self, task_type, page_size=None, q=None):
        """ 按优先级排序后随机获取任务大厅的任务列表"""

        def get_random_skip():
            condition.update(dict(priority=3))
            n3 = self.db.task.count_documents(condition)
            condition.update(dict(priority=2))
            n2 = self.db.task.count_documents(condition)
            condition.pop('priority', 0)
            skip = n3 if n3 > page_size else n3 + n2 if n3 + n2 > page_size else total_count
            return random.randint(1, skip - page_size) if skip > page_size else 0

        def de_duplicate():
            """ 组任务去重"""
            _tasks, _doc_ids = [], []
            for task in tasks:
                if task.get('doc_id') not in _doc_ids:
                    _tasks.append(task)
                    _doc_ids.append(task.get('doc_id'))
            return _tasks[:page_size]

        page_size = page_size or self.prop(self.config, 'pager.page_size', 10)
        condition = {'doc_id': {'$regex': q, '$options': '$i'}} if q else {}
        if self.is_group(task_type):
            condition.update({'task_type': {'$regex': task_type}, 'status': self.STATUS_PUBLISHED})
            # 去掉同组的我的任务
            my_tasks = self.find_mine(task_type)
            if my_tasks:
                condition['doc_id'] = condition.get('doc_id') or {}
                condition['doc_id'].update({'$nin': [t['doc_id'] for t in my_tasks]})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_random_skip()
            # 按3倍量查询后去重
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
            tasks = de_duplicate()
        else:
            condition.update({'task_type': task_type, 'status': self.STATUS_PUBLISHED})
            total_count = self.db.task.count_documents(condition)
            skip_no = get_random_skip()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks, total_count

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
            condition.update({'picked_user_id': self.user_id})
        return self.db.task.count_documents(condition)

    def get_publish_meta(self, task_type):
        now = self.now()
        collection, id_name = self.get_data_conf(task_type)[:2]
        return dict(
            task_type=task_type, batch='', collection=collection, id_name=id_name, doc_id='',
            status='', priority='', steps={}, pre_tasks=[], input=None, result={},
            create_time=now, updated_time=now, publish_time=now,
            publish_user_id=self.user_id,
            publish_by=self.username
        )

    def init_steps(self, task, task_type=None):
        """ 检查当前任务的步骤，缺省时自动填充默认设置，有误时报错
        当前步骤可以在url中申明，或者在api的请求体中给出。
        """
        steps = dict()
        default_steps = self.get_steps(task_type)
        todo = self.prop(task, 'steps.todo') or default_steps
        submitted = self.prop(task, 'steps.submitted') or []
        un_submitted = [s for s in todo if s not in submitted]
        current_step = (self.get_query_arguments('step') or [''])[0] or self.prop(self.data, 'step', '')
        if todo:
            if current_step and current_step not in todo:
                current_step = todo[0]
            if not current_step:
                current_step = un_submitted[0] if self.mode == 'do' and not self.is_api else todo[0]
            index = todo.index(current_step)
            steps['todo'] = todo
            steps['current'] = current_step
            steps['is_first'] = index == 0
            steps['is_last'] = index == len(todo) - 1
            steps['prev'] = todo[index - 1] if index > 0 else None
            steps['next'] = todo[index + 1] if index < len(todo) - 1 else None
        else:
            steps['todo'] = []
            steps['current'] = None
            steps['is_first'] = True
            steps['is_last'] = True
            steps['prev'] = None
            steps['next'] = None
        return steps

    def check_task_auth(self, task, mode=None):
        """ 检查当前用户是否拥有相应的任务权限"""
        mode = self.get_task_mode() if not mode else mode
        error = None
        if mode in ['do', 'update']:
            if not task:
                error = e.task_not_existed
            elif task.get('picked_user_id') != self.current_user.get('_id'):
                error = e.task_unauthorized_locked
            elif mode == 'do' and task['status'] != self.STATUS_PICKED:
                error = e.task_can_only_do_picked
            elif mode == 'update' and task['status'] != self.STATUS_FINISHED:
                error = e.task_can_only_update_finished
        has_auth = error is None
        return has_auth, error

    def check_my_lock(self):
        """ 检查当前用户是否拥有相应的数据锁并进行分配
        has_lock为None表示不需要数据锁，False表示获取失败，True表示获取成功
        """
        shared_field = self.get_shared_field(self.task_type)
        has_lock, error = None, None
        # do模式下，检查是否有任务锁
        if shared_field and self.mode == 'do':
            lock = self.prop(self.doc, 'lock.' + shared_field)
            assert lock
            has_lock = self.user_id == self.prop(lock, 'locked_user_id')
            if not has_lock:
                error = e.data_is_locked
        # update/模式下，尝试分配临时数据锁
        if shared_field and self.mode in ['update', 'edit']:
            r = self.assign_temp_lock(self.doc_id, shared_field, self.current_user, self.doc)
            has_lock = r is True
            error = None if has_lock else r
        return has_lock, error

    def update_task(self, submit, info=None):
        """ 更新任务提交"""
        if not submit:
            if info:
                self.db.task.update_one({'_id': ObjectId(self.task_id)}, {'$set': info})
        else:
            update = info if info else {}
            update.update({'updated_time': self.now()})
            if self.steps['todo']:
                update['steps.submitted'] = self.get_submitted(self.steps['current'])
            # 如果是任务多个子步骤的中间步骤
            if len(self.steps['todo']) > 1 and not self.steps['is_last']:
                self.db.task.update_one({'_id': ObjectId(self.task_id)}, {'$set': update})
            # 如果任务没有子步骤，或一个步骤，或多个步骤的最后一步
            else:
                if self.mode == 'do':
                    self.finish_task(self.task, info)
                elif self.mode == 'update':
                    self.db.task.update_one({'_id': ObjectId(self.task_id)}, {'$set': update})

    def get_submitted(self, step):
        """ 更新task.steps.submitted字段"""
        submitted = self.prop(self.task, 'steps.submitted', [])
        if step not in submitted:
            submitted.append(step)
        return submitted

    def finish_task(self, task, info=None):
        """ 完成任务"""
        # 更新当前任务
        info = info or {}
        info.update({'status': self.STATUS_FINISHED, 'finished_time': self.now()})
        self.db.task.update_one({'_id': task['_id']}, {'$set': info})
        # 更新后置任务
        doc_tasks = list(self.db.task.find({
            'collection': task['collection'], 'id_name': task['id_name'], 'doc_id': task['doc_id']
        }))
        finished_types = [t['task_type'] for t in doc_tasks if t['status'] == self.STATUS_FINISHED]
        for _task in doc_tasks:
            # 更新_task的pre_tasks
            pre_tasks = self.prop(_task, 'pre_tasks', {})
            pre_tasks.update({p: self.STATUS_FINISHED for p in pre_tasks if p in finished_types})
            _update = {'pre_tasks': pre_tasks}
            # 如果_task状态为悬挂，且pre_tasks均已完成，则修改状态为已发布
            unfinished = [v for v in pre_tasks.values() if v != self.STATUS_FINISHED]
            if _task['status'] == self.STATUS_PENDING and not unfinished:
                _update.update({'status': self.STATUS_PUBLISHED})
                # 更新_task关联数据的tasks字段
                self.update_task_doc(_task, status=self.STATUS_PUBLISHED)
            self.db.task.update_one({'_id': _task['_id']}, {'$set': _update})

    def update_doc(self, info, submit=None):
        """ 更新本任务的数据提交"""
        submit = self.data.get('submit') if submit is None else submit
        # 如果是完成任务，则更新数据内容、数据等级和数据任务状态
        if submit and self.mode == 'do' and self.steps['is_last']:
            self.update_task_doc(self.task, True, True, self.STATUS_FINISHED, info)
        # 非完成任务，仅更新数据内容
        else:
            self.update_task_doc(self.task, info=info)

    def update_task_doc(self, task, update_level=False, release_lock=False, status=None, info=None):
        """ 更新任务的doc数据
        :param task, 数据所属的任务
        :param update_level, 是否更新doc的level.task_type
        :param release_lock, 是否释放任务锁
        :param status, doc的tasks.task_type的状态
        :param info, doc的其它字段
        """
        if not task.get('doc_id'):
            return
        info = {} if not info else info
        task_type = task['task_type']
        collection, id_name = self.get_data_conf(task_type)[:2]
        # 检查共享字段
        shared_field = self.get_shared_field(task_type)
        if shared_field:
            # 释放数据锁
            if release_lock:
                info['lock.' + shared_field] = dict()
            # 更新数据等级
            lock_level = self.get_lock_level(shared_field, task_type)
            if update_level and lock_level:
                info['level.' + shared_field] = lock_level
        # 更新任务状态
        if status:
            info['tasks.' + task_type] = status
        if status == '':
            self.db[collection].update_one({id_name: task['doc_id']}, {'$unset': {'tasks.' + task_type: ''}})
        if info:
            self.db[collection].update_one({id_name: task['doc_id']}, {'$set': info})

    def update_edit_doc(self, task_type, doc_id, release_lock=False, info=None):
        """ 更新数据编辑的doc数据
        :param task_type, 以哪种任务类型进行数据编辑
        :param doc_id, doc的id值
        :param release_lock, 是否释放临时锁
        :param info, doc的其它字段
        """
        info = {} if not info else info
        # 释放数据锁
        shared_field = self.get_shared_field(task_type)
        if release_lock and shared_field:
            info['lock.' + shared_field] = dict()
        # 更新数据库
        collection, id_name = self.get_data_conf(task_type)[:2]
        self.db[collection].update_one({id_name: doc_id}, {'$set': info})
