#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务基础Handler。
@time: 2019/10/16
"""
import re
from datetime import datetime
from controller import auth
from controller import errors as e
from controller.task.task import Task
from controller.base import BaseHandler


class TaskHandler(BaseHandler, Task):
    def get_task_mode(self):
        return (re.findall('(do|update|edit)/', self.request.path) or ['view'])[0]

    def check_task_auth(self, task, mode=None):
        """ 检查当前用户是否拥有相应的任务权限 """
        mode = self.get_task_mode() if not mode else mode
        error = None
        if mode in ['do', 'update']:
            if task.get('picked_user_id') != self.current_user.get('_id'):
                error = e.task_unauthorized_locked
            elif mode == 'do' and task['status'] != self.STATUS_PICKED:
                error = e.task_can_only_do_picked
            elif mode == 'update' and task['status'] != self.STATUS_FINISHED:
                error = e.task_can_only_update_finished
        has_auth = error is None
        return has_auth, error

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
        query = self.db.task.find(condition)
        if size:
            query.limit(size)
        return list(query)

    def finish_task(self, task):
        """ 任务提交 """
        # 更新当前任务
        update = {'status': self.STATUS_FINISHED, 'finished_time': datetime.now()}
        self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        self.add_op_log('submit_%s' % task['task_type'], target_id=task['_id'])
        # 释放数据锁，并更新数据等级
        self.release_task_lock(task, update_level=True)
        # 更新后置任务
        condition = dict(collection=task['collection'], id_name=task['id_name'], doc_id=task['doc_id'])
        tasks = list(self.db.task.find(condition))
        finished_types = [t['task_type'] for t in tasks if t['status'] == self.STATUS_FINISHED]
        for task in tasks:
            # 检查任务task的所有前置任务的状态
            pre_tasks = self.prop(task, 'pre_tasks', {})
            pre_tasks.update({p: self.STATUS_FINISHED for p in pre_tasks if p in finished_types})
            update = {'pre_tasks': pre_tasks}
            # 如果当前任务为悬挂，且所有前置任务均已完成，则修改状态为已发布
            unfinished = [v for v in pre_tasks.values() if v != self.STATUS_FINISHED]
            if task['status'] == self.STATUS_PENDING and not unfinished:
                update.update({'status': self.STATUS_OPENED})
            self.db.task.update_one({'_id': task['_id']}, {'$set': update})

    """ 数据锁介绍
    1）数据锁的目的：
      通过数据锁对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
      1.tasks。同一数据的同阶任务（如cut_proof对chars而言）或高阶任务（如text_proof对chars而言）
      2.roles。数据专家角色对所有page的授权字段
    2）数据锁的时效：
      1.长时数据锁，由系统在领取任务时自动分配，在提交或退回任务时自动释放；
      2.临时数据锁，用户自己提交任务后update数据或者高阶任务用户以及专家edit数据时分配临时数据锁，在窗口离开时解锁，或定时自动回收。
    3）数据锁的配置：
      1.首先在task_shared_data_fields中注册需要共享的数据字段；
      2.然后在data_auth_maps中配置，授权给相关的tasks或者roles访问。
    4) 数据锁的分配策略：
      1.长时数据锁权限高于临时数据锁。分配长时数据锁时，将忽略临时数据锁的存在，以便任务的正常开展
      2.分配数据锁时，只有申请者的数据等级大于等于数据的当前等级时，才能分配数据锁
    """
    # 数据锁权限配置表。在对共享数据进行写操作时，需要检查数据锁资质，以这个表来判断。
    # tasks: 共享字段授权的任务，仅对任务关联的数据有效。
    # roles: 共享字段授权的角色，对所有数据有效。
    # level: 数据等级
    data_auth_maps = {
        'box': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['chars', 'columns', 'blocks'],
            'tasks': ['cut_proof', 'cut_review', 'ocr_text', 'text_proof', 'text_review', 'text_hard'],
            'roles': ['切分专家'],
            'level': dict(cut_proof=1, cut_review=10, ocr_text=10, text_proof=10, text_review=100,
                          text_hard=100, 切分专家=100),
        },
        'text': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['text', 'txt_html'],
            'tasks': ['text_review', 'text_hard'],
            'roles': ['文字专家'],
            'level': dict(text_review=1, text_hard=1, 文字专家=10),
        },
    }

    @classmethod
    def get_conf_level(cls, shared_field, task_type):
        return cls.prop(cls.data_auth_maps, '%s.level.%s' % (shared_field, task_type))

    def get_user_qualification(self, doc_id, shared_field):
        """ 检查用户是否有数据锁资质并返回资质 """
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']

        # 检查当前用户是否有数据锁对应的专家角色
        user_roles = auth.get_all_roles(self.current_user['roles'])
        roles = set(user_roles) & set(shared_field_meta['roles'])
        if roles:
            return dict(lock_type='role', auth=list(roles))

        # 检查当前用户是否有该数据的同阶或高阶任务
        user_tasks = self.db.task.find({
            'collection': collection, 'id_name': id_name, 'doc_id': doc_id,
            'picked_user_id': self.current_user['_id'],
            'status': {'$ne': self.STATUS_RETURNED}
        })
        tasks = set(t['task_type'] for t in user_tasks) & set(shared_field_meta['tasks'])
        if tasks:
            return dict(lock_type='task', auth=list(tasks))

    def get_qualification_level(self, shared_field, qualifications):
        level_conf = self.prop(self.data_auth_maps, shared_field + '.level')
        return max([int(self.prop(level_conf, q, 0)) for q in qualifications])

    def get_data_lock_and_level(self, doc_id, shared_field):
        """ 获取当前数据锁及数据等级"""
        assert shared_field in self.data_auth_maps
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']
        doc = self.db[collection].find_one({id_name: doc_id})
        return self.prop(doc, 'lock.' + shared_field, {}), int(self.prop(doc, 'lock.level.' + shared_field, 0))

    def assign_temp_lock(self, doc_id, shared_field):
        """ 将临时数据锁分配给当前用户。成功时返回True，失败时返回错误代码 """
        lock, level = self.get_data_lock_and_level(doc_id, shared_field)
        # 检查是否已有数据锁
        if lock:
            return True if lock.get('locked_user_id') == self.current_user['_id'] else e.data_is_locked
        # 检查数据资质及数据等级
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']
        qualification = self.get_user_qualification(doc_id, shared_field)
        if not qualification:
            return e.data_lock_unqualified
        conf_level = self.get_qualification_level(shared_field, qualification.get('auth'))
        if conf_level < level:
            return e.lock_level_unqualified
        # 分配数据锁
        r = self.db[collection].update_one({id_name: doc_id}, {'$set': {'lock.' + shared_field: {
            'is_temp': True, 'qualification': qualification,
            'locked_user_id': self.current_user['_id'],
            'locked_by': self.current_user['name'],
            'locked_time': datetime.now(),
        }}})
        return True if r.matched_count else e.data_lock_failed

    def release_temp_lock(self, doc_id, shared_field):
        """ 释放用户的数据锁 """
        assert shared_field in self.data_auth_maps
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']
        condition = {'lock.%s.locked_user_id' % shared_field: self.current_user['_id'],
                     id_name: doc_id, 'lock.%s.is_temp' % shared_field: True}
        r = self.db[collection].update_many(condition, {'$set': {'lock.%s' % shared_field: dict()}})
        return r.matched_count

    def assign_task_lock(self, doc_id, shared_field, task_type):
        """ 将数据的长时数据锁分配给任务。成功时返回True，失败时返回错误代码。
        如果数据锁已经分配给了其它任务，则分配失败。分配任务数据锁时，将忽略临时数据锁。
        """
        lock, level = self.get_data_lock_and_level(doc_id, shared_field)
        # 检查数据锁是否已分配给其它任务
        if lock and lock.get('is_temp') is False:
            return e.data_is_locked
        # 检查数据资质及数据等级
        if task_type not in self.prop(self.data_auth_maps, '%s.tasks' % shared_field):
            return e.data_lock_unqualified
        conf_level = self.prop(self.data_auth_maps, '%s.level.%s' % (shared_field, task_type), 0)
        if conf_level < level:
            return e.lock_level_unqualified
        # 分配数据锁并设置数据等级
        qualification = dict(lock_type='task', tasks=task_type)
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']
        lock = {'is_temp': False, 'qualification': qualification, 'locked_time': datetime.now(),
                'locked_by': self.current_user['name'], 'locked_user_id': self.current_user['_id']}
        r = self.db[collection].update_one({id_name: doc_id}, {'$set': {
            'lock.' + shared_field: lock, 'lock.level.' + shared_field: conf_level,
        }})
        return True if r.matched_count else e.data_lock_failed

    def release_task_lock(self, task, update_level=False):
        """ 释放任务的数据锁 """
        shared_field = self.get_shared_field(task['task_type'])
        if not shared_field:
            return
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']
        condition = {'lock.%s.locked_user_id' % shared_field: self.current_user['_id'],
                     id_name: task['doc_id'], 'lock.%s.is_temp' % shared_field: False}
        update = {'lock.%s' % shared_field: dict()}
        if update_level:
            conf_level = self.prop(self.data_auth_maps, '%s.level.%s' % (shared_field, task['task_type']), 0)
            update.update({'lock.level.%s' % shared_field: conf_level})
        r = self.db[collection].update_many(condition, {'$set': update})
        return r.matched_count

    def check_data_lock(self, task=None, doc_id=None, shared_field=None, mode=None):
        """ 检查当前用户是否拥有相应的数据锁 """
        if task:
            doc_id, shared_field = task['doc_id'], self.get_shared_field(task['task_type'])
        mode = self.get_task_mode() if not mode else mode
        has_lock, error = True, None
        if shared_field and mode == 'do':
            lock = self.get_data_lock_and_level(doc_id, shared_field)[0]
            has_lock = self.current_user['_id'] == self.prop(lock, 'locked_user_id')
            error = e.data_unauthorized
        if shared_field and mode in ['update', 'edit']:
            r = self.assign_temp_lock(doc_id, shared_field)
            has_lock = r is True
            error = r
        return has_lock, error
