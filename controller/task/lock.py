#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据锁
1）数据锁的目的：通过数据锁对共享的数据字段进行写保护，以下两种情况可以分配字段对应的数据锁：
  1.tasks。同一数据的同阶任务（如cut_proof对chars而言）或高阶任务（如text_proof对chars而言）
  2.roles。专家用户对所有page的授权字段
2）数据锁的时效：
  1.长时数据锁，由系统在领取任务时自动分配，在提交或退回任务时自动释放；
  2.临时数据锁，用户自己提交任务后update数据或者高阶任务用户以及专家edit数据时分配临时数据锁，在窗口离开时解锁，或定时自动回收。
3）数据锁的配置：
  1.首先在task_shared_data_fields中注册需要共享的数据字段；
  2.然后在data_auth_maps中配置，授权给相关的tasks或者roles访问。
4) 数据锁的分配策略：
  1.长时数据锁权限高于临时数据锁。分配长时数据锁时，将忽略临时数据锁的存在，以便任务的正常开展
  2.分配数据锁时，只有申请者的数据等级大于等于数据的当前等级时，才能分配数据锁
@time: 2019/10/16
"""
from datetime import datetime
from controller import auth
from controller import errors as e
from controller.helper import prop
from controller.task.task import Task


class Lock(object):
    def __init__(self, **kwargs):
        self.db = None

    # 数据锁权限配置表。在对共享数据进行写操作时，需要检查数据锁资质，以这个表来判断。
    # tasks: 共享字段授权的任务，仅对任务关联的数据有效。
    # roles: 共享字段授权的角色，对所有数据有效。
    # level: 数据等级
    data_auth_maps = {
        'box': {
            'collection': 'page', 'id': 'name', 'protect_fields': ['chars', 'columns', 'blocks'],
            'tasks': ['cut_proof', 'cut_review', 'ocr_text', 'text_proof_1', 'text_proof_2', 'text_proof_3',
                      'text_review', 'text_hard'],
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
    def get_lock_level(cls, shared_field, task_type):
        """ 获取数据等级"""
        return prop(cls.data_auth_maps, '%s.level.%s' % (shared_field, task_type))

    @classmethod
    def get_collection_and_id(cls, shared_field):
        shared_field_meta = cls.data_auth_maps[shared_field]
        return shared_field_meta['collection'], shared_field_meta['id']

    def get_user_qualification(self, user, doc_id, shared_field):
        """ 检查用户是否有数据锁资质并返回资质 """
        shared_field_meta = self.data_auth_maps[shared_field]
        id_name, collection = shared_field_meta['id'], shared_field_meta['collection']

        # 检查用户是否数据锁对应的专家角色
        user_roles = auth.get_all_roles(user['roles'])
        roles = set(user_roles) & set(shared_field_meta['roles'])
        if roles:
            return dict(lock_type='role', auth=list(roles))

        # 检查当前用户是否有该数据的同阶或高阶任务
        user_tasks = self.db.task.find({
            'collection': collection, 'id_name': id_name, 'doc_id': doc_id, 'picked_user_id': user['_id'],
            'status': {'$ne': Task.STATUS_RETURNED}
        })
        tasks = set(t['task_type'] for t in user_tasks) & set(shared_field_meta['tasks'])
        if tasks:
            return dict(lock_type='task', auth=list(tasks))

    @classmethod
    def get_qualification_level(cls, shared_field, qualifications):
        """ 从多个数据资质中，获取最大的数据等级"""
        level_conf = prop(cls.data_auth_maps, shared_field + '.level')
        return max([int(prop(level_conf, q, 0)) for q in qualifications])

    def get_data_lock_and_level(self, doc_id, shared_field, doc=None):
        """ 获取数据的当前锁及数据等级"""
        assert shared_field in self.data_auth_maps
        collection, id_name = self.get_collection_and_id(shared_field)
        doc = self.db[collection].find_one({id_name: doc_id}) if not doc else doc
        return prop(doc, 'lock.' + shared_field, {}), int(prop(doc, 'level.' + shared_field, 0))

    def assign_temp_lock(self, doc_id, shared_field, user, doc=None):
        """ 将临时数据锁分配给用户。成功时返回True，失败时返回错误代码 """
        lock, level = self.get_data_lock_and_level(doc_id, shared_field, doc)
        # 检查是否已有数据锁
        if lock:
            return True if lock.get('locked_user_id') == user['_id'] else e.data_is_locked
        # 检查数据资质及数据等级
        collection, id_name = self.get_collection_and_id(shared_field)
        qualification = self.get_user_qualification(user, doc_id, shared_field)
        if not qualification:
            return e.data_lock_unqualified
        lock_level = self.get_qualification_level(shared_field, qualification.get('auth'))
        if lock_level < level:
            return e.data_level_unqualified
        # 分配数据锁
        r = self.db[collection].update_one({id_name: doc_id}, {'$set': {'lock.' + shared_field: {
            'is_temp': True, 'qualification': qualification, 'locked_time': datetime.now(),
            'locked_user_id': user['_id'], 'locked_by': user['name'],
        }}})
        return True if r.matched_count else e.data_lock_failed

    def release_temp_lock(self, doc_id, shared_field, user=None):
        """ 释放用户的临时数据锁 """
        assert shared_field in self.data_auth_maps
        collection, id_name = self.get_collection_and_id(shared_field)
        condition = {id_name: doc_id, 'lock.%s.is_temp' % shared_field: True}
        if user:
            condition.update({'lock.%s.locked_user_id' % shared_field: user['_id']})
        r = self.db[collection].update_many(condition, {'$set': {'lock.%s' % shared_field: dict()}})
        return r.matched_count

    def assign_task_lock(self, doc_id, task_type, user):
        """ 将数据的长时数据锁分配给任务。成功时返回True，失败时返回错误代码。
            如果数据锁已经分配给了其它任务，则分配失败。分配任务数据锁时，将忽略临时数据锁。
        """
        shared_field = Task.get_shared_field(task_type)
        if not shared_field:
            return
        lock, level = self.get_data_lock_and_level(doc_id, shared_field)
        # 检查数据锁是否已分配给其它任务
        if lock and lock.get('is_temp') is False:
            return e.data_is_locked
        # 检查数据资质及数据等级
        if task_type not in prop(self.data_auth_maps, '%s.tasks' % shared_field):
            return e.data_lock_unqualified
        lock_level = prop(self.data_auth_maps, '%s.level.%s' % (shared_field, task_type), 0)
        if lock_level < level:
            return e.data_level_unqualified
        # 分配数据锁
        qualification = dict(lock_type='task', tasks=task_type)
        collection, id_name = self.get_collection_and_id(shared_field)
        r = self.db[collection].update_one({id_name: doc_id}, {'$set': {'lock.' + shared_field: {
            'is_temp': False, 'qualification': qualification, 'locked_time': datetime.now(),
            'locked_by': user['name'], 'locked_user_id': user['_id']
        }}})
        return True if r.matched_count else e.data_lock_failed
