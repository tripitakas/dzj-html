#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务Handler基类
    1. 任务状态。
    任务依赖的数据由TaskHandler.task_types.input_field定义，如果该数据就绪，则可以发布任务。
    如果没有前置任务，则直接发布，状态为“opened”；如果有前置任务，则悬挂，状态为“pending”。
    用户领取任务后，状态为“picked”，退回任务后，状态为“returned”，提交任务后，状态为“finished”。
    2. 前置任务
    任务配置表中定义了默认的前置任务。
    业务管理员在发布任务时，可以对前置任务进行修改，比如文字审定需要两次或者三次校对。发布任务后，任务的前置任务将记录在数据库中。
    如果任务包含前置任务，系统发布任务后，状态为“pending”。当前置任务状态都变为“finished”时，自动将当前任务发布为“opened”。
    3. 发布任务
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、文档集合（doc_ids）。
@time: 2019/3/11
"""
from datetime import datetime
import controller.auth as auth
import controller.errors as errors
from controller.base import BaseHandler


class TaskHandler(BaseHandler):
    # 任务类型定义表。
    # pre_tasks：默认的前置任务
    # data.collection：任务所对应数据表
    # data.id：数据表的主键名称
    # data.input_field：该任务依赖的数据字段，该字段就绪，则可以发布任务
    # data.shared_field：该任务共享和保护的数据字段
    task_types = {
        'cut_proof': {
            'name': '切分校对',
            'steps': {'char_box': '字框', 'block_box': '栏框', 'column_box': '列框', 'char_order': '字序'},
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'chars'},
        },
        'cut_review': {
            'name': '切分审定', 'pre_tasks': ['cut_proof'],
            'steps': {'char_box': '字框', 'block_box': '栏框', 'column_box': '列框', 'char_order': '字序'},
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'chars', 'shared_field': 'chars'},
        },
        'text_proof_1': {
            'name': '文字校一',
            'steps': {'select_compare_text': '选择比对文本', 'proof': '文字校对'},
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
        },
        'text_proof_2': {
            'name': '文字校二',
            'steps': {'select_compare_text': '选择比对文本', 'proof': '文字校对'},
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
        },
        'text_proof_3': {
            'name': '文字校三',
            'steps': {'select_compare_text': '选择比对文本', 'proof': '文字校对'},
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
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

    # 任务组定义表。
    # 对于同一数据的一组任务而言，用户只能领取其中的一个。
    # 在任务大厅和我的任务中，任务组中的任务将合并显示。
    # 任务组仅在以上两处起作用，不影响其他任务管理功能。
    task_groups = {
        'text_proof': {
            'name': '文字校对',
            'data': {'collection': 'page', 'id': 'name', 'input_field': 'ocr'},
            'groups': ['text_proof_1', 'text_proof_2', 'text_proof_3']
        },
    }

    # 数据锁权限配置表。在update或edit操作时，需要检查数据锁资质，以这个表来判断。
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
    STATUS_PUBLISHED = 'published'
    data_status_names = {
        STATUS_UNREADY: '未就绪', STATUS_TODO: '待办', STATUS_READY: '已就绪', STATUS_PUBLISHED: '已发布'
    }

    # 任务优先级
    prior_names = {3: '高', 2: '中', 1: '低'}

    @classmethod
    def prop(cls, obj, key):
        for s in key.split('.'):
            obj = obj.get(s) if isinstance(obj, dict) else None
        return obj

    @classmethod
    def all_task_types(cls):
        task_types = cls.task_types.copy()
        task_types.update(cls.task_groups)
        return task_types

    @classmethod
    def task_names(cls):
        return {k: v.get('name') for k, v in cls.all_task_types().items()}

    @classmethod
    def step_names(cls):
        step_names = dict()
        for t in cls.task_types.values():
            step_names.update(t.get('steps') or {})
        return step_names

    @classmethod
    def task_meta(cls, task_type):
        d = cls.task_types.get(task_type)['data']
        return d['collection'], d['id'], d.get('input_field'), d.get('shared_field')

    def find_tasks(self, task_type, doc_id=None, status=None, size=None, mine=False):
        assert task_type in self.task_types
        collection, id_name = self.task_meta(task_type)[:2]
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

    def check_auth(self, task_type, mode, doc_id):
        """ 检查当前用户是否拥有任务的权限以及数据锁
        :return 如果mode为do或update，而用户没有任务权限，则直接抛出错误
                如果mode为do或update或edit，而用户没有获得数据锁，则返回False，表示没有写权限
                其余情况，返回True，表示通过授权检查
        """
        assert task_type in self.task_types
        collection, id_name, input_field, shared_field = self.task_meta(task_type)
        # do/update模式下，需要检查任务权限，直接抛出错误
        if mode in ['do', 'update']:
            render = '/api' not in self.request.path and not self.get_query_argument('_raw', 0)
            # 检查任务是否已分配给当前用户
            collection, id_name = self.task_meta(task_type)[:2]
            task = self.db.task.find_one(dict(collection=collection, id_name=id_name, doc_id=doc_id,
                                              task_type=task_type, picked_user_id=self.current_user['_id']))
            if not self.current_user or not task:
                return self.send_error_response(errors.task_unauthorized, render=render, reason=doc_id)
            # 检查任务状态以及是否为进行中或已完成（已完成的任务可以update）
            if task['status'] not in [self.STATUS_PICKED, self.STATUS_FINISHED]:
                return self.send_error_response(errors.task_unauthorized, render=render, reason=doc_id)
            if mode == 'do' and task['status'] == self.STATUS_FINISHED:
                return self.send_error_response(errors.task_finished_not_allowed_do, render=render, reason=doc_id)

        # do/update/edit模式下，需要检查数据锁（在配置表中申明的字段才进行检查）
        auth = False
        if mode in ['do', 'update', 'edit']:
            if not shared_field or shared_field not in self.data_auth_maps:  # 无共享字段或共享字段没有在授权表中
                auth = True
            elif (self.has_data_lock(collection, id_name, doc_id, shared_field)
                  or self.get_data_lock(collection, id_name, doc_id, shared_field) is True):
                auth = True

        return auth

    def finish_task(self, task_type, doc_id):
        """ 完成任务提交 """
        # 更新当前任务
        collection, id_name = self.task_meta(task_type)[:2]
        update = {'status': self.STATUS_FINISHED, 'finished_time': datetime.now()}
        condition = dict(task_type=task_type, collection=collection, id_name=id_name, doc_id=doc_id,
                         picked_user_id=self.current_user['_id'], status=self.STATUS_PICKED)
        self.db.task.update_one(condition, {'$set': update})
        ret = {'finished': True}

        # 释放数据锁
        shared_field = self.get_shared_field(task_type)
        if shared_field and shared_field in self.data_auth_maps:
            update['lock.' + shared_field] = {}
            self.db[collection].update_one({id_name: doc_id}, {'$set': update})
            ret['data_lock_released'] = True

        # 更新后置任务
        self.update_post_tasks(doc_id, task_type)
        ret['post_tasks_updated'] = True

        return ret

    def update_post_tasks(self, task_type, doc_id):
        """ 任务完成提交后，更新后置任务的状态 """
        assert task_type in self.task_types
        collection, id_name = self.task_meta(task_type)[:2]
        condition = dict(task_type=task_type, collection=collection, id_name=id_name, doc_id=doc_id)
        for task in self.db.task.find(condition):
            pre_tasks = task.get('pre_tasks', {})
            if task_type in pre_tasks:
                pre_tasks[task_type] = self.STATUS_FINISHED
                unfinished_pre_tasks = [v for v in pre_tasks.values() if v != self.STATUS_FINISHED]
                update = {'pre_task.%s' % task_type: self.STATUS_FINISHED}
                # 如果当前任务状态为悬挂，且所有前置任务均已完成，则设置状态为已发布
                if task['status'] == self.STATUS_PENDING and not unfinished_pre_tasks:
                    update.update({'status': self.STATUS_OPENED})
                self.db.task.update_one({'_id', task['_id']}, {'$set': update})

    """ 数据锁介绍
    1）数据锁的目的：通过数据锁对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
      1.tasks。同一page的同阶任务（如cut_proof对chars而言）或高阶任务（如text_proof对chars而言）
      2.roles。数据专家角色对所有page的授权字段
    2）数据锁的类型：
      1.长时数据锁，由系统在领取任务时自动分配，在提交或退回任务时自动释放；
      2.临时数据锁，用户自己提交任务后update数据或者高阶任务用户以及专家edit数据时分配临时数据锁，在窗口离开时解锁，或定时自动回收。
    3）数据锁的使用：
      1.首先在task_shared_data_fields中注册需要共享的数据字段；
      2.然后在data_auth_maps中配置，授权给相关的tasks或者roles访问。
    4) 数据锁的存储：存储在数据记录的lock字段中。比如page表的数据锁，就存在page表的lock字段中。
    """

    @classmethod
    def get_shared_field(cls, task_type):
        """ 获取任务保护的共享字段 """
        return cls.prop(cls.task_types, '%s.shared_field' % task_type)

    def has_data_lock(self, collection, id_name, doc_id, data_field, is_temp=None):
        """ 检查当前用户是否拥有某数据锁
        :param collection 数据表，即mongodb的collection
        :param id_name 作为id的字段名称
        :param doc_id 作为id的字段值
        :param data_field 检查哪个数据字段
        :param is_temp 是否为临时锁
         """
        assert is_temp in [None, True, False]
        condition = {id_name: doc_id, 'lock.%s.locked_user_id' % data_field: self.current_user['_id']}
        if is_temp is not None:
            condition.update({'lock.%s.is_temp' % data_field: is_temp})
        n = self.db[collection].count_documents(condition)
        return n > 0

    def is_data_locked(self, collection, id_name, doc_id, shared_field):
        """检查数据是否已经被锁定"""
        data = self.db[collection].find_one({id_name: doc_id})
        return True if self.prop(data, 'lock.%s.locked_user_id' % shared_field) else False

    def get_data_lock(self, collection, id_name, doc_id, shared_field):
        """ 将临时数据锁分配给当前用户。（长时数据锁由系统在任务领取时分配，是任务提交时释放）。
        :return 成功时返回True，失败时返回errors.xxx。

        """

        def assign_lock(lock_type):
            """ lock_type指的是来自哪个任务或者哪个角色 """
            r = self.db[collection].update_one({id_name: doc_id}, {'$set': {
                'lock.' + shared_field: {
                    "is_temp": True,
                    "lock_type": lock_type,
                    "locked_by": self.current_user['name'],
                    "locked_user_id": self.current_user['_id'],
                    "locked_time": datetime.now(),
                }
            }})
            return r.matched_count > 0

        assert shared_field in self.data_auth_maps
        # 如果当前用户已有数据锁，则直接返回
        if self.has_data_lock(collection, id_name, doc_id, shared_field):
            return True
        # 检查当前用户是否有数据锁对应的角色（有一个角色即可）
        user_all_roles = auth.get_all_roles(self.current_user['roles'])
        roles = list(set(user_all_roles) & set(self.data_auth_maps[shared_field]['roles']))
        if roles:
            if not self.is_data_locked(collection, id_name, doc_id, shared_field):
                return True if assign_lock(dict(roles=roles)) else errors.data_lock_failed
            else:
                return errors.data_is_locked
        # 获取当前用户拥有的该数据的所有任务
        tasks = self.db.task.find_one({'data': dict(collection=collection, id_name=id_name, doc_id=doc_id)})
        my_tasks = [t for t in tasks if t.get('picked_user_id') == self.current_user['_id']
                    and t.get('status') != self.STATUS_RETURNED]
        # 检查当前用户是否有该数据的同阶或高阶任务
        tasks = list(set(my_tasks) & set(self.data_auth_maps[shared_field]['tasks']))
        if tasks:
            if not self.is_data_locked(collection, id_name, doc_id, shared_field):
                return True if assign_lock(dict(tasks=tasks)) else errors.data_lock_failed
            else:
                return errors.data_is_locked

        return errors.data_unauthorized

    def release_data_lock(self, collection, id_name, doc_id, shared_field, is_temp=True):
        """ 释放数据锁 """
        if shared_field in self.data_auth_maps and self.has_data_lock(
                collection, id_name, doc_id, shared_field, is_temp=is_temp):
            self.db[collection].update_one({id_name: doc_id}, {'$set': {'lock.%s' % shared_field: dict()}})
