#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
import json
from bson.objectid import ObjectId
from controller import errors as e
from controller import validate as v
from controller.task.base import TaskHandler
from controller.auth import can_access, get_all_roles


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type):
        """ 领取任务"""
        try:
            # 检查是否有未完成的任务
            uncompleted = self.find_mine(task_type, 1, status=self.STATUS_PICKED)
            if uncompleted:
                url = '/task/do/%s/%s' % (uncompleted[0]['task_type'], uncompleted[0]['_id'])
                return self.send_error_response(e.task_uncompleted, **{'url': url, 'doc_id': uncompleted[0]['doc_id']})

            task_id, task = self.prop(self.data, 'task_id'), None
            if task_id:
                task = self.db.task.find_one({'_id': ObjectId(task_id)})
                if not task:
                    return self.send_error_response(e.no_object, message='没有找到该任务')
                if task['status'] != self.STATUS_PUBLISHED:
                    return self.send_error_response(e.task_not_published)
            else:
                # 如果task_id为空，则从任务大厅任取一个
                tasks = self.find_lobby(task_type, page_size=1)[0]
                if not tasks:
                    return self.send_error_response(e.no_task_to_pick)
                task = tasks[0]

            # 如果任务为组任务，则检查用户是否曾领取过该组任务
            if self.is_group(task_type) and self.db.task.find_one(dict(
                    status={'$in': [self.STATUS_FINISHED, self.STATUS_PICKED]}, doc_id=task['doc_id'],
                    picked_user_id=self.user_id, task_type={'$regex': task_type},
            )):
                message = '您曾领取过本页面组任务中的一个，不能再领取其它任务'
                return self.send_error_response(e.group_task_duplicated, message=message)
            # 分配数据锁
            r = self.assign_task_lock(task['doc_id'], task_type, self.current_user)
            if isinstance(r, tuple):
                return self.send_error_response(r)
            # 分配任务
            self.db.task.update_one({'_id': task['_id']}, {'$set': {
                'status': self.STATUS_PICKED, 'picked_user_id': self.user_id, 'picked_by': self.username,
                'picked_time': self.now(), 'updated_time': self.now(),
            }})
            self.add_log('pick_task', target_id=task['_id'], context=task['task_type'])
            # 更新doc
            self.update_task_doc(task, status=self.STATUS_PICKED)
            # 设置返回参数
            url = '/task/do/%s/%s' % (task['task_type'], task['_id'])
            return self.send_data_response({'url': url, 'doc_id': task['doc_id'], 'task_id': task['_id']})

        except self.DbError as error:
            return self.send_db_error(error)


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_id'

    def post(self, task_id):
        """ 退回任务"""
        try:
            if self.task['picked_user_id'] != self.user_id:
                return self.send_error_response(e.unauthorized, message='您没有该任务的权限')
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'return_reason': self.prop(self.data, 'reason', ''),
                'status': self.STATUS_RETURNED,
                'updated_time': self.now(),
            }})
            self.update_task_doc(self.task, release_lock=True, status=self.STATUS_RETURNED)

            self.add_log('return_task', target_id=self.task['_id'])
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class UpdateTaskApi(TaskHandler):
    URL = '/api/task/(batch|remark)'

    def post(self, field):
        """ 批量更新任务批次或备注"""
        try:
            rules = [(v.not_both_empty, '_ids', '_id'), (v.not_both_empty, 'batch', 'remark')]
            self.validate(self.data, rules)

            update = {field: self.data[field]}
            if self.data.get('_id'):
                if self.data.get('is_sample'):
                    update['is_sample'] = True if self.data['is_sample'] == '是' else False
                r = self.db.task.update_one({'_id': ObjectId(self.data['_id'])}, {'$set': update})
                self.add_log('update_task', target_id=self.data['_id'], context=self.data[field])
            else:
                _ids = [ObjectId(t) for t in self.data['_ids']]
                r = self.db.task.update_many({'_id': {'$in': _ids}}, {'$set': update})
                self.add_log('update_task', target_id=_ids, context=self.data[field])
            self.send_data_response(dict(count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class RepublishTaskApi(TaskHandler):
    URL = '/api/task/republish/@task_id'

    def post(self, task_id):
        """ 重新发布任务"""
        try:
            if self.task.get('status') not in [self.STATUS_PICKED, self.STATUS_FAILED]:
                self.send_error_response(e.task_status_error, message='只能重新发布进行中或失败的任务')
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'pre_tasks': {k: '' for k in self.prop(self.task, 'pre_tasks', [])},
                'status': self.STATUS_PUBLISHED, 'result': {}
            }})
            self.db.task.update_one({'_id': self.task['_id']}, {'$unset': {k: '' for k in [
                'steps.submitted', 'picked_user_id', 'picked_by', 'picked_time', 'return_reason'
            ]}})
            self.update_task_doc(self.task, release_lock=True, status=self.STATUS_PUBLISHED)

            self.add_log('republish_task', target_id=self.task['_id'])
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete'

    def post(self):
        """ 删除任务(只能删除已发布未领取、等待前置任务、已退回的任务，这些任务未占数据锁)"""
        try:
            rules = [(v.not_both_empty, '_ids', '_id')]
            self.validate(self.data, rules)

            _ids = self.data['_ids'] if self.data.get('_ids') else [self.data['_id']]
            status = [self.STATUS_PUBLISHED, self.STATUS_PENDING, self.STATUS_RETURNED]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in _ids]}, 'status': {'$in': status}}))
            r = self.db.task.delete_many({'_id': {'$in': [t['_id'] for t in tasks]}})
            self.add_log('delete_task', target_id=_ids)
            # 更新doc
            for task in tasks:
                self.update_task_doc(task, release_lock=True, status='')
            return self.send_data_response({'count': r.deleted_count})

        except self.DbError as error:
            return self.send_db_error(error)


class AssignTasksApi(TaskHandler):
    URL = '/api/task/assign'

    @staticmethod
    def can_user_access(task_type, user):
        user_roles = ','.join(get_all_roles(user.get('roles')))
        return can_access(user_roles, '/api/task/pick/%s' % task_type, 'POST')

    def post(self):
        """ 批量指派已发布的任务给某用户
        :param tasks, 格式为 [[_id, task_type, doc_id], ]
        :return dict, 如{'un_existed':[], 'un_published':[], 'lock_failed':[], 'assigned':[]}
        """
        try:
            rules = [(v.not_empty, 'tasks', 'user_id')]
            self.validate(self.data, rules)
            user = self.db.user.find_one({'_id': ObjectId(self.data['user_id'])})
            if not user:
                return self.send_error_response(e.no_user)

            log, lock_failed, assigned = dict(), [], []
            now, user_id, user_name = self.now(), user['_id'], user['name']
            # 去掉用户无权访问的任务
            log['unauthorized'] = [t[2] for t in self.data['tasks'] if not self.can_user_access(t[1], user)]
            authorized = [t[0] for t in self.data['tasks'] if self.can_user_access(t[1], user)]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in authorized]}}))
            # 去掉不存在的任务
            log['un_existed'] = set(authorized) - set([str(t['_id']) for t in tasks])
            # 去掉未发布的任务
            log['un_published'] = [t['doc_id'] for t in tasks if t['status'] != self.STATUS_PUBLISHED]
            published = [t for t in tasks if t['status'] == self.STATUS_PUBLISHED]
            # 去掉用户已领取的文字校对页面
            text_proof_tasks = [t['doc_id'] for t in published if 'text_proof' in t['task_type']]
            log['duplicated_text'] = set(d for d in text_proof_tasks if text_proof_tasks.count(d) > 1)
            published = [t for t in published if t['doc_id'] not in log['duplicated_text']]
            text_proof_tasks = set(text_proof_tasks) - log['duplicated_text']
            if text_proof_tasks:
                user_picked_tasks = self.find_mine('text_proof', user_id=user_id)
                log['picked_before'] = set(t['doc_id'] for t in user_picked_tasks) & set(text_proof_tasks)
                published = [t for t in published if t['doc_id'] not in log['picked_before']]
            # 指派已发布的任务
            for task in published:
                # 尝试分配数据锁
                shared_field = self.get_shared_field(task['task_type'])
                if shared_field and task.get('doc_id'):
                    r = self.assign_task_lock(task['doc_id'], task['task_type'], user)
                    if r is not True:
                        lock_failed.append(task['doc_id'] + ':' + r[1])
                        continue
                # 分配任务
                self.db.task.update_one({'_id': task['_id']}, {'$set': {
                    'status': self.STATUS_PICKED, 'picked_user_id': user_id, 'picked_by': user_name,
                    'picked_time': now, 'updated_time': now,
                }})
                assigned.append(task['doc_id'])
                # 更新doc的任务状态
                self.update_task_doc(task, status=self.STATUS_PICKED)

            log['lock_failed'] = lock_failed
            log['assigned'] = assigned
            self.add_log('assign_task', context='%s, %s' % (user_id, assigned))
            self.send_data_response({k: v for k, v in log.items() if v})

        except self.DbError as error:
            return self.send_db_error(error)


class FinishTaskApi(TaskHandler):
    URL = '/api/task/finish/@task_id'

    def post(self, task_id):
        """ 提交任务，释放数据锁，并且更新后置任务状态。仅供测试使用"""
        try:
            self.finish_task(self.task)
            self.update_task_doc(self.task, True, True, self.STATUS_FINISHED, {})
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
