#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务基础表。
@time: 2019/10/16
"""
import re
from datetime import datetime
from controller import auth
from controller import errors as e
from controller.model import Model
from controller import validate as v
from controller.base import BaseHandler


class TaskHandler(BaseHandler, Model):
    # 数据库定义
    collection = 'task'
    fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'task_type', 'name': '任务类型'},
        {'id': 'collection', 'name': '任务关联的文档集合'},
        {'id': 'id_name', 'name': '文档键名'},
        {'id': 'doc_id', 'name': '文档键值'},
        {'id': 'status', 'name': '任务状态'},
        {'id': 'priority', 'name': '任务优先级'},
        {'id': 'steps', 'name': '任务步骤'},
        {'id': 'pre_tasks', 'name': '前置任务'},
        {'id': 'lock', 'name': '数据锁'},
        {'id': 'input', 'name': '任务输入参数'},
        {'id': 'result', 'name': '任务输出结果'},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_user_id', 'name': '发布人id'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_user_id', 'name': '领取人id'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    rules = [
        (v.not_empty, 'task_type', 'name'),
    ]
    primary = '_id'

    # 前端列表页面定义
    search_fields = ['doc_id']
    operations = [  # 列表包含哪些批量操作
        {'operation': 'bat-assign', 'label': '批量指派'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    actions = [  # 列表单条记录包含哪些操作
        {'action': 'btn-view', 'label': '查看'},
        {'action': 'btn-update', 'label': '修改'},
        {'action': 'btn-remove', 'label': '删除'},
    ]

    # 任务类型定义
    # pre_tasks：默认的前置任务
    # data.collection：任务所对应数据表
    # data.id：数据表的主键名称
    # data.input_field：任务所依赖的数据字段。如果该字段不为空，则可以发布任务
    # data.shared_field：任务共享和保护的数据字段
    task_types = {
        'import_image': {
            'name': '导入图片',
        },
        'upload_cloud': {
            'name': '上传云端',
            'data': {'collection': 'page', 'id': 'name'},
        },
        'ocr_box': {
            'name': 'OCR字框',
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'box'},
        },
        'cut_proof': {
            'name': '切分校对', 'pre_tasks': ['ocr_box', 'upload_cloud'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['block_box', '栏框'], ['char_box', '字框'], ['column_box', '列框'], ['char_order', '字序']],
        },
        'cut_review': {
            'name': '切分审定', 'pre_tasks': ['cut_proof'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'box'},
            'steps': [['block_box', '栏框'], ['char_box', '字框'], ['column_box', '列框'], ['char_order', '字序']],
        },
        'ocr_text': {
            'name': 'OCR文字', 'pre_tasks': ['cut_review'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
        'text_proof_1': {
            'name': '文字校一', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_proof_2': {
            'name': '文字校二', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_proof_3': {
            'name': '文字校三', 'pre_tasks': ['ocr_text'],
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
        },
        'text_review': {
            'name': '文字审定', 'pre_tasks': ['text_proof_1', 'text_proof_2', 'text_proof_3'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
        'text_hard': {
            'name': '难字审定', 'pre_tasks': ['text_review'],
            'data': {'collection': 'page', 'id': 'name', 'shared_field': 'text'},
        },
    }

    # 任务组定义。对于同一数据的一组任务而言，用户只能领取其中的一个。
    # 在任务大厅和我的任务中，任务组中的任务将合并显示。
    # 任务组仅在以上两处起作用，不影响其他任务管理功能。
    task_groups = {
        'text_proof': {
            'name': '文字校对',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'steps': [['select_compare_text', '选择比对文本'], ['proof', '文字校对']],
            'groups': ['text_proof_1', 'text_proof_2', 'text_proof_3']
        },
    }

    # 任务状态表
    STATUS_OPENED = 'opened'
    STATUS_PENDING = 'pending'
    STATUS_FETCHED = 'fetched'  # 已获取。小欧获取任务后尚未进行确认时的状态
    STATUS_PICKED = 'picked'
    STATUS_FAILED = 'failed'  # 失败。小欧执行任务失败时的状态
    STATUS_RETURNED = 'returned'
    STATUS_FINISHED = 'finished'
    task_status_names = {
        STATUS_OPENED: '已发布未领取', STATUS_PENDING: '等待前置任务', STATUS_FETCHED: '已获取',
        STATUS_PICKED: '进行中', STATUS_FAILED: '失败', STATUS_RETURNED: '已退回',
        STATUS_FINISHED: '已完成',
    }

    # 任务优先级
    priority_names = {3: '高', 2: '中', 1: '低'}

    """ 数据锁介绍
    1）数据锁的目的：通过数据锁对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
      1.tasks。同一数据的同阶任务（如cut_proof对chars而言）或高阶任务（如text_proof对chars而言）
      2.roles。数据专家角色对所有page的授权字段
    2）数据锁的类型：
      1.长时数据锁，由系统在领取任务时自动分配，在提交或退回任务时自动释放；
      2.临时数据锁，用户自己提交任务后update数据或者高阶任务用户以及专家edit数据时分配临时数据锁，在窗口离开时解锁，或定时自动回收。
    3）数据锁的使用：
      1.首先在task_shared_data_fields中注册需要共享的数据字段；
      2.然后在data_auth_maps中配置，授权给相关的tasks或者roles访问。
    4) 数据锁的存储：存储在数据记录的lock字段中。比如page表的数据锁，就存在page表的lock字段中。
    """
    # 数据锁权限配置表。在对共享数据进行写操作时，需要检查数据锁资质，以这个表来判断。
    # tasks: 共享字段授权的任务，仅对任务关联的数据有效
    # roles: 共享字段授权的角色，对所有数据有效
    # level: 数据等级。用户的数据等级大于等于当前数据等级时，才可以分配数据锁
    data_auth_maps = {
        'box': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['chars', 'columns', 'blocks'],
            'tasks': ['cut_proof', 'cut_review', 'text_proof', 'text_review', 'text_hard'],
            'roles': ['切分专家'],
            'level': {'cut_proof': 1, 'cut_review': 10, 'text_proof': 10, 'text_review': 100,
                      'text_hard': 100, '切分专家': 100},
        },
        'text': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['text', 'txt_html'],
            'tasks': ['text_review', 'text_hard'],
            'roles': ['文字专家'],
            'level': {'text_review': 1, 'text_hard': 10, '文字专家': 10},
        },
    }

    @classmethod
    def all_task_types(cls):
        task_types = cls.task_types.copy()
        task_types.update(cls.task_groups)
        return task_types

    @classmethod
    def get_task_meta(cls, task_type):
        return cls.all_task_types().get(task_type)

    @classmethod
    def get_shared_field(cls, task_type):
        """ 获取任务保护的共享字段 """
        return cls.prop(cls.task_types, '%s.data.shared_field' % task_type)

    @classmethod
    def get_task_data_conf(cls, task_type):
        d = cls.prop(cls.all_task_types(), '%s.data' % task_type) or dict()
        return d.get('collection'), d.get('id'), d.get('input_field'), d.get('shared_field')

    @classmethod
    def get_page_tasks(cls):
        return [t for t, v in cls.task_types.items() if cls.prop(v, 'data.collection') == 'page']

    @classmethod
    def task_names(cls):
        return {k: v.get('name') for k, v in cls.all_task_types().items()}

    @classmethod
    def get_task_name(cls, task_type):
        return cls.task_names().get(task_type)

    @classmethod
    def step_names(cls):
        step_names = dict()
        for t in cls.task_types.values():
            for step in t.get('steps', []):
                step_names.update({step[0]: step[1]})
        return step_names

    @classmethod
    def get_step_name(cls, step):
        return cls.step_names().get(step)

    @classmethod
    def get_status_name(cls, status):
        return cls.task_status_names.get(status)

    @classmethod
    def get_priority_name(cls, priority):
        return cls.priority_names.get(priority)

    @classmethod
    def get_field_name(cls, field):
        for f in cls.fields:
            if f['id'] == field:
                return f['name']

    @classmethod
    def init_steps(cls, task, mode, cur_step=''):
        """ 检查当前任务的步骤，缺省时进行设置，有误时报错 """
        todo = cls.prop(task, 'steps.todo') or []
        submitted = cls.prop(task, 'steps.submitted') or []
        un_submitted = [s for s in todo if s not in submitted]
        if not todo:
            return e.task_steps_is_empty
        if cur_step and cur_step not in todo:
            return e.task_step_error
        if not cur_step:
            cur_step = un_submitted[0] if mode == 'do' else todo[0]

        steps = dict()
        index = todo.index(cur_step)
        steps['current'] = cur_step
        steps['is_first'] = index == 0
        steps['is_last'] = index == len(todo) - 1
        steps['prev'] = todo[index - 1] if index > 0 else None
        steps['next'] = todo[index + 1] if index < len(todo) - 1 else None
        return steps

    def find_tasks(self, task_type, doc_id=None, status=None, size=None, mine=False):
        collection, id_name = self.get_task_data_conf(task_type)[:2]
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
        self.add_op_log('submit_%s' % task['task_type'], target_id=task['_id'])

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

    def get_task_mode(self):
        return (re.findall('(do|update|edit)/', self.request.path) or ['view'])[0]

    def check_task_auth(self, task, mode=None):
        """ 检查当前用户是否拥有相应的任务权限 """
        mode = self.get_task_mode() if not mode else mode
        has_auth, error = False, None
        if mode in ['do', 'update']:
            if task.get('picked_user_id') != self.current_user.get('_id'):
                error = e.task_unauthorized_locked
            elif mode == 'do' and task['status'] != self.STATUS_PICKED:
                error = e.task_can_only_do_picked
            elif mode == 'update' and task['status'] != self.STATUS_FINISHED:
                error = e.task_can_only_update_finished
        has_auth = error is None
        return has_auth, error

    def check_task_lock(self, task, mode=None):
        """ 检查当前用户是否拥有相应的数据锁 """
        mode = self.get_task_mode() if not mode else mode
        has_lock, error = False, None
        if mode in ['do', 'update', 'edit']:
            shared_field = self.get_shared_field(task['task_type'])
            if shared_field and shared_field in self.data_auth_maps:
                lock = self.get_data_lock(task['doc_id'], shared_field)
                has_lock, error = lock is True, lock
        return has_lock, error

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
            return e.data_is_locked

        qualification = self.get_lock_qualification(doc_id, shared_field)
        if qualification is False:
            return e.unauthorized

        return True if assign_lock(qualification) else e.data_lock_failed

    def release_temp_lock(self, doc_id, shared_field=None):
        """ 释放用户的临时数据锁 """
        assert isinstance(doc_id, str)
        assert shared_field in self.data_auth_maps
        id_name = self.data_auth_maps[shared_field]['id']
        collection = self.data_auth_maps[shared_field]['collection']

        if self.has_data_lock(doc_id, shared_field):
            self.db[collection].update_one({id_name: doc_id}, {'$set': {'lock.%s' % shared_field: dict()}})

    @classmethod
    def release_task_lock(cls, db, doc_ids, shared_field):
        """ 释放任务的数据锁 """
        assert isinstance(doc_ids, list)
        assert shared_field in cls.data_auth_maps
        id_name = cls.data_auth_maps[shared_field]['id']
        collection = cls.data_auth_maps[shared_field]['collection']
        db[collection].update_many({id_name: {'$in': doc_ids}}, {'$set': {'lock.%s' % shared_field: dict()}})
