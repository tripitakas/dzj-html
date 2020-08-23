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
            content = dict(task_type=self.task['task_type'])
            self.add_log('return_task', target_id=self.task['_id'], content=content)
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
                self.add_log('update_task', target_id=self.data['_id'], content=update)
            else:
                _ids = [ObjectId(t) for t in self.data['_ids']]
                r = self.db.task.update_many({'_id': {'$in': _ids}}, {'$set': update})
                self.add_log('update_task', target_id=_ids, content=update)
            self.send_data_response(dict(count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class RepublishTaskApi(TaskHandler):
    URL = ['/api/task/republish', '/api/task/republish/@task_id']

    def post(self, task_id=None):
        """ 重新发布任务"""
        try:
            ids = [task_id] if task_id else self.data['ids']
            if not ids:
                return self.send_error_response(e.no_object, message='没有指定任务id参数')
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(i) for i in ids]}},
                                           {'status': 1, 'task_type': 1, 'doc_id': 1}))
            if not tasks:
                return self.send_error_response(e.no_object, message='没有找到任务')
            statuses = [self.STATUS_PICKED, self.STATUS_FAILED]
            if task_id and tasks[0].get('status') not in statuses:
                return self.send_error_response(e.task_status_error, message='只能重新发布已完成或失败的任务')
            task_ids = [t['_id'] for t in tasks if t['status'] in statuses]
            r = self.db.task.update_many({'_id': {'$in': task_ids}, 'status': {'$in': task_ids}},
                                         {'$set': {'status': self.STATUS_PUBLISHED, 'result': {}},
                                          '$unset': {k: '' for k in [
                                              'steps.submitted', 'picked_user_id', 'picked_by', 'picked_time',
                                              'return_reason', 'message'
                                          ]}})  # pre_tasks 不用再改变?

            if task_id:
                self.update_page_status(self.STATUS_PUBLISHED)
            self.add_log('republish_task', target_id=tasks[0]['_id'],
                         content=dict(task_type=tasks[0]['task_type'], doc_id=tasks[0].get('doc_id') or ''),
                         remark='%d tasks' % r.modified_count)
            return self.send_data_response(published_count=r.modified_count)

        except self.DbError as error:
            return self.send_db_error(error)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete'

    def post(self):
        """ 删除任务(只能删除已发布未领取、已获取、等待前置任务、已退回的任务)"""
        try:
            rules = [(v.not_both_empty, '_ids', '_id')]
            self.validate(self.data, rules)

            _ids = self.data['_ids'] if self.data.get('_ids') else [self.data['_id']]
            status = [self.STATUS_PUBLISHED, self.STATUS_FETCHED, self.STATUS_PENDING, self.STATUS_RETURNED]
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
                return self.send_error_response(e.no_user, message=e.no_user[1] + ' (%s)' % self.data['user_id'])
            type_count = len(set(t[1] for t in self.data['tasks']))
            if type_count > 1:
                return self.send_error_response(e.task_type_error, message='一次只能指派一种任务类型')

            task_type = self.data['tasks'][0][1]
            collection = self.prop(self.task_types, task_type + '.data.collection')
            key = 'doc_id' if collection == 'page' else 'txt_kind'
            log, assigned = dict(), []
            now, user_id, username = self.now(), user['_id'], user['name']
            # 去掉用户无权访问的任务
            log['unauthorized'] = [t[2] for t in self.data['tasks'] if not self.can_user_access(t[1], user)]
            authorized = [t[0] for t in self.data['tasks'] if t[2] not in log['unauthorized']]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in authorized]}}))
            # 去掉不存在的任务
            log['un_existed'] = set(authorized) - set([str(t['_id']) for t in tasks])
            # 去掉非「已发布」的任务
            log['un_published'] = [t.get(key, '') for t in tasks if t['status'] != self.STATUS_PUBLISHED]
            published = [t for t in tasks if t['status'] == self.STATUS_PUBLISHED]
            if collection == 'page':
                # 去掉用户曾领取过的任务
                published_docs = [t['doc_id'] for t in published]
                cond = {'task_type': task_type, 'doc_id': {'$in': published_docs}, 'picked_user_id': user_id}
                tasks = list(self.db.task.find(cond, {'doc_id': 1}))
                log['picked_before'] = [t['doc_id'] for t in tasks] if tasks else []
                published = [t for t in published if t['doc_id'] not in log['picked_before']]
            # 指派已发布的任务
            self.db.task.update_many({'_id': {'$in': [t['_id'] for t in published]}}, {'$set': {
                'status': self.STATUS_PICKED, 'picked_user_id': user_id, 'picked_by': username,
                'picked_time': now, 'updated_time': now,
            }})
            log['assigned'] = [t[key] for t in published]
            # 更新page的任务状态
            if collection == 'page':
                for t in published:
                    self.update_page_status(self.STATUS_PICKED, t)
            self.send_data_response({k: i for k, i in log.items() if i})
            self.add_log('assign_task', [t['_id'] for t in published], None,
                         dict(task_type=task_type, username=username, doc_id=[t.get(key) for t in published]))

        except self.DbError as error:
            return self.send_db_error(error)


class FinishTaskApi(TaskHandler):
    URL = '/api/task/finish/@oid'

    def post(self, task_id):
        """ 完成任务，供测试用例使用"""
        try:
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            self.update_post_tasks(self.task)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class InitTasksForOPTestApi(TaskHandler):
    URL = '/api/task/init4op'

    def post(self):
        """ 初始化数据处理任务，以便OP平台进行测试。注意：该API仅仅是配合OP平台测试使用"""
        rules = [(v.not_empty, 'page_names', 'import_dirs', 'layout')]
        self.validate(self.data, rules)

        try:
            tasks, task_types = [], ['import_image', 'ocr_box', 'ocr_text', 'upload_cloud']
            # 清空数据处理任务
            self.db.task.delete_many({'task_type': {'$in': task_types}})
            # 创建导入图片任务
            for import_dir in self.data['import_dirs']:
                task = self.get_publish_meta('import_image')
                params = dict(import_dir=import_dir, redo=True, layout=self.data['layout'])
                task.update(dict(task_type='import_image', status='published', params=params))
                tasks.append(task)
            # 创建其它类型的任务
            for task_type in ['ocr_box', 'ocr_text', 'upload_cloud']:
                for page_name in self.data['page_names']:
                    task = self.get_publish_meta(task_type)
                    task.update(dict(task_type=task_type, batch='测试批次', status='published', doc_id=page_name))
                    if task_type == 'ocr_text':
                        page = self.db.page.find_one({'name': page_name})
                        if page:
                            task['params'] = {k: page[k] for k in ['blocks', 'columns', 'chars']}
                    tasks.append(task)
            r = self.db.task.insert_many(tasks)
            if r.inserted_ids:
                self.send_data_response(dict(ids=r.inserted_ids))

        except self.DbError as error:
            return self.send_db_error(error)
