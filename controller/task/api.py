#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
                tasks = self.find_lobby(task_type, page_size=1)[0]
                if not tasks:
                    return self.send_error_response(e.no_task_to_pick)
                task = tasks[0]

            # 如果任务有多个校次，则检查用户是否曾领取过某校次
            if task.get('doc_id') and self.has_num(task_type) and self.db.task.find_one(dict(
                    task_type=task_type, status={'$in': [self.STATUS_FINISHED, self.STATUS_PICKED]},
                    doc_id=task['doc_id'], picked_user_id=self.user_id,
            )):
                message = '您曾领取过本任务中的某校次，不能再领取其它校次。'
                return self.send_error_response(e.group_task_duplicated, message=message)
            # 分配任务
            self.db.task.update_one({'_id': task['_id']}, {'$set': {
                'status': self.STATUS_PICKED, 'picked_user_id': self.user_id, 'picked_by': self.username,
                'picked_time': self.now(), 'updated_time': self.now(),
            }})
            # 更新页面
            self.update_page_status(self.STATUS_PICKED, task)

            url = '/task/do/%s/%s' % (task['task_type'], task['_id'])
            return self.send_data_response({'url': url, 'doc_id': task.get('doc_id'), 'task_id': task['_id']})

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
            self.update_page_status(self.STATUS_RETURNED)
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
            self.update_page_status(self.STATUS_PUBLISHED)
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

            for task in tasks:
                self.update_page_status(None, task)
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
        """ 批量指派已发布的任务给某用户，一次只能指派一种任务类型
        :param tasks, 格式为 [[_id, task_type, doc_id], ]
        :return dict, 如{'un_existed':[], 'un_published':[], 'lock_failed':[], 'assigned':[]}
        """
        try:
            rules = [(v.not_empty, 'tasks', 'user_id')]
            self.validate(self.data, rules)
            user = self.db.user.find_one({'_id': ObjectId(self.data['user_id'])})
            if not user:
                return self.send_error_response(e.no_user)
            type_count = len(set(t[1] for t in self.data['tasks']))
            if type_count > 1:
                return self.send_error_response(e.task_type_error, message='一次只能指派一种任务类型')

            task_type = self.data['tasks'][1]
            collection = self.prop(self.task_types, task_type + '.collection')
            log, lock_failed, assigned = dict(), [], []
            now, user_id, user_name = self.now(), user['_id'], user['name']
            # 去掉用户无权访问的任务
            log['unauthorized'] = [t[2] for t in self.data['tasks'] if not self.can_user_access(t[1], user)]
            authorized = [t[0] for t in self.data['tasks'] if self.can_user_access(t[1], user)]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in authorized]}}))
            # 去掉不存在的任务
            log['un_existed'] = set(authorized) - set([str(t['_id']) for t in tasks])
            # 去掉非「已发布」的任务
            log['un_published'] = [t['doc_id'] for t in tasks if t['status'] != self.STATUS_PUBLISHED]
            published = [t for t in tasks if t['status'] == self.STATUS_PUBLISHED]
            # 去掉用户曾领取过的任务
            cond = {'task_type': task_type, 'doc_id': {'$in': [t[2] for t in published], 'picked_user_id': user_id}}
            tasks = list(self.db.task.find(cond, {'doc_id': 1}))
            log['picked_before'] = [t['doc_id'] for t in tasks] if tasks else []
            # 指派已发布的任务
            to_assign = [t for t in published if t['doc_id'] not in log['picked_before']]
            self.db.task.update_one({'_id': [t['_id'] for t in to_assign]}, {'$set': {
                'status': self.STATUS_PICKED, 'picked_user_id': user_id, 'picked_by': user_name,
                'picked_time': now, 'updated_time': now,
            }})
            log['assigned'] = [t['doc_id'] for t in to_assign]
            # 更新page的任务状态
            if collection == 'page':
                for t in to_assign:
                    self.update_page_status(self.STATUS_PICKED, t)
            self.add_log('assign_task', context='%s, %s' % (user_id, assigned))
            self.send_data_response({k: i for k, i in log.items() if i})

        except self.DbError as error:
            return self.send_db_error(error)
