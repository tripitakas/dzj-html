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

    def check_auth(self, task, mode):
        """ 检查当前用户是否拥有相应的任务权限及数据锁
        :return 如果mode为do或update，而用户没有任务权限，则直接抛出错误
                如果mode为do或update或edit，而用户没有获得数据锁，则返回False，表示没有写权限
                其余情况，返回True，表示通过授权检查
        """
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

        # 检查数据锁
        auth = False
        if mode in ['do', 'update', 'edit']:
            s = self.get_shared_field(task['task_type'])
            c, i, d = task['collection'], task['id_name'], task['doc_id']
            if not s or s not in self.data_auth_maps:  # 无共享字段或共享字段没有在授权表中
                auth = True
            elif self.has_data_lock(c, i, d, s) or self.get_data_lock(c, i, d, s) is True:
                auth = True

        return auth

    def finish_task(self, task):
        """ 完成任务提交 """
        # 更新当前任务
        ret = {'finished': True}
        update = {'status': self.STATUS_FINISHED, 'finished_time': datetime.now()}
        self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        # 释放数据锁
        shared_field = self.get_shared_field(task['task_type'])
        if shared_field and shared_field in self.data_auth_maps:
            update['lock.' + shared_field] = {}
            self.db[task['collection']].update_one({task['id_name']: task['doc_id']}, {'$set': update})
            ret['data_lock_released'] = True
        # 更新后置任务
        self.update_post_tasks(task)
        ret['post_tasks_updated'] = True

        return ret

    def update_post_tasks(self, task):
        """ 任务完成提交后，更新后置任务的状态 """
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

    def has_data_lock(self, collection, id_name, doc_id, shared_field, is_temp=None):
        """ 检查当前用户是否拥有某数据锁
        :param collection 数据表，即mongodb的collection
        :param id_name 作为id的字段名称
        :param doc_id 作为id的字段值
        :param shared_field 检查哪个数据字段
        :param is_temp 是否为临时锁
         """
        assert is_temp in [None, True, False]
        condition = {id_name: doc_id, 'lock.%s.locked_user_id' % shared_field: self.current_user['_id']}
        if is_temp is not None:
            condition.update({'lock.%s.is_temp' % shared_field: is_temp})
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

        # 检查当前用户是否已有数据锁
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
        # 检查当前用户是否有该数据的同阶或高阶任务
        tasks = self.db.task.find_one({'data': dict(collection=collection, id_name=id_name, doc_id=doc_id)})
        my_tasks = [t for t in tasks if t.get('picked_user_id') == self.current_user['_id']
                    and t.get('status') != self.STATUS_RETURNED]
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
