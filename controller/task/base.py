#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler
一、mode 任务模式
1. do，做任务：用户做任务时，进入该模式
2. update，更新任务：用户完成任务后，可以通过update模式进行修改
3. view，查看任务：非任务所有者可以通过view模式来查看任务
4. browse，浏览任务：管理员可以通过browse模式来逐条浏览任务
二、 url
1. do/update/browse，如：/task/(do/update/browse)/@task_type/5e3139c6a197150011d65e9d
2. view，如：/task/@task_type/5e3139c6a197150011d65e9d
@time: 2019/10/16
"""
import re
import random
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.task import Task
from controller.base import BaseHandler


class TaskHandler(BaseHandler, Task):
    def __init__(self, application, request, **kwargs):
        super(TaskHandler, self).__init__(application, request, **kwargs)
        self.task = self.task_type = self.steps = self.task_id = None
        self.mode = self.readonly = self.submit_by_page = None

    def prepare(self):
        """ 根据url参数，检查任务是否存在并设置任务，检查任务权限，设置任务相关参数"""
        super().prepare()
        if not self.get_task_id():
            return
        self.task_id = self.get_task_id()
        self.task, self.error = self.get_task(self.task_id)
        if not self.task:
            return self.send_error_response(self.error)
        self.task_id = str(self.task['_id'])
        self.mode = self.get_task_mode()
        if self.mode in ['do', 'update']:
            has_auth, self.error = self.check_task_auth(self.task)
            if not has_auth:
                links = [('查看', re.sub('/(do|update)/', '/', self.request.uri))]
                return self.send_error_response(self.error, links=links)
        self.task_type = self.get_task_type()
        self.steps = self.init_steps(self.task, self.task_type)
        self.readonly = self.mode in ['view', 'browse', '', None]

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
        return s.group(1) if (s and '/task/' in self.request.uri) else ''

    def get_task_mode(self):
        r = re.findall('/task/(do|update|browse)/', self.request.path)
        mode = r[0] if r else 'view' if self.get_task_id() else None
        return mode

    def get_task_type(self):
        """ 获取任务类型。子类可重载，以便prepare函数调用"""
        # eg. /task/do/cut_proof/5e3139c6a197150011d65e9d
        s = re.search(r'/task/(do|update|browse)/([^/]+?)/([0-9a-z]{24})', self.request.path)
        task_type = s.group(2) if s else ''
        return task_type

    def task_name(self):
        return self.get_task_name(self.task_type) or self.task_type

    def step_name(self):
        return self.get_step_name(self.steps.get('current')) or ''

    def find_many(self, task_type=None, status=None, size=None, order=None):
        """ 查找任务"""
        condition = dict()
        if task_type:
            condition.update({'task_type': task_type})
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
        condition = {'picked_user_id': user_id or self.user_id}
        if task_type:
            condition.update({'task_type': task_type})
        if status:
            condition.update({'status': status or {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]}})
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

        page_size = page_size or self.prop(self.config, 'pager.page_size', 10)
        field = 'doc_id' if task_type in self.get_page_tasks() else 'txt_kind'
        condition = {field: {'$regex': q, '$options': '$i'}} if q else {}
        condition.update({'task_type': task_type, 'status': self.STATUS_PUBLISHED})
        total_count = self.db.task.estimated_document_count(filter=condition)
        if self.has_num(task_type):  # 任务类型有多个校次的情况
            tasks = []
            my_tasks = self.find_mine(task_type)
            while len(tasks) < page_size:
                not_allowed = [t[field] for t in my_tasks + tasks] if (my_tasks or tasks) else []
                if not_allowed:
                    condition[field] = condition.get(field) or {}
                    condition[field].update({'$nin': not_allowed})
                skip_no = get_random_skip()
                tasks_in_db = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size * 3))
                if not tasks_in_db:
                    break
                for t in tasks_in_db:
                    if t[field] not in [t[field] for t in tasks]:
                        tasks.append(t)
        else:
            condition.update({'task_type': task_type, 'status': self.STATUS_PUBLISHED})
            skip_no = get_random_skip()
            tasks = list(self.db.task.find(condition).skip(skip_no).sort('priority', -1).limit(page_size))

        return tasks[:page_size], total_count

    def count_task(self, task_type=None, status=None, mine=False):
        """ 统计任务数量"""
        condition = dict()
        if task_type:
            condition.update({'task_type': task_type})
        if status:
            condition.update({'status': {'$in': [status] if isinstance(status, str) else status}})
        if mine:
            con_status = condition.get('status') or {}
            con_status.update({'$ne': self.STATUS_RETURNED})
            condition.update({'status': con_status})
            condition.update({'picked_user_id': self.user_id})
        return self.db.task.estimated_document_count(filter=condition)

    def check_task_auth(self, task, mode=None):
        """ 检查当前用户是否拥有相应的任务权限"""
        mode = self.get_task_mode() if not mode else mode
        error = None
        if mode in ['do', 'update']:
            if not task:
                error = e.task_not_existed
            elif task.get('picked_user_id') != self.current_user.get('_id'):
                error = e.task_has_been_picked
            elif mode == 'do' and task['status'] != self.STATUS_PICKED:
                error = e.task_can_only_do_picked
            elif mode == 'update' and task['status'] != self.STATUS_FINISHED:
                error = e.task_can_only_update_finished
        has_auth = error is None
        return has_auth, error

    def init_steps(self, task, task_type=None):
        """ 检查当前任务的步骤，缺省时自动填充默认设置，有误时报错
        当前步骤可以在url中申明，或者在api的请求体中给出。
        """
        steps = dict()
        task_type = task_type or task['task_type']
        default_steps = self.prop(self.task_types, task_type + '.steps') or []
        default_steps = default_steps and [s[0] for s in default_steps]
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
            steps['current'] = current_step
            steps['is_first'] = True
            steps['is_last'] = True
            steps['prev'] = None
            steps['next'] = None
        return steps

    def update_page_status(self, status, task=None):
        """ 更新任务相关的页面数据"""
        task = task or self.task or {}
        if task.get('collection') == 'page' and task.get('doc_id'):
            num = '_' + str(task['num']) if task.get('num') else ''
            task_type = task['task_type'] + num
            if status:
                self.db.page.update_one({'name': task['doc_id']}, {'$set': {'tasks.' + task_type: status}})
            else:
                self.db.page.update_one({'name': task['doc_id']}, {'$unset': {'tasks.' + task_type: ''}})
