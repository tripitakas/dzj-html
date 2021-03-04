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
        """领取任务"""
        try:
            # 检查是否有未完成的任务
            uncompleted = self.find_mine(task_type, 1, status=self.STATUS_PICKED)
            if uncompleted:
                url = '/task/do/%s/%s' % (uncompleted[0]['task_type'], uncompleted[0]['_id'])
                return self.send_error_response(e.task_uncompleted, **{'url': url, 'doc_id': uncompleted[0]['doc_id']})
            # 领取指定任务
            task_id, task = self.prop(self.data, 'task_id'), None
            if task_id:
                group_types = self.get_group_types(task_type)
                task = self.db.task.find_one({'_id': ObjectId(task_id)})
                if task and self.has_num(task_type) and self.db.task.find_one({
                    'doc_id': task['doc_id'], 'picked_user_id': self.user_id,
                    'task_type': {'$in': group_types} if group_types else task_type,
                    'status': {'$in': [self.STATUS_FINISHED, self.STATUS_PICKED]}
                }):
                    task = None  # 不可以重复领取同组(相同doc_id)任务
            # 系统分配任务
            for i in range(5):
                if not task or task['status'] != self.STATUS_PUBLISHED:
                    task = self.pick_one(task_type, self.prop(self.current_user, 'task_batch.%s' % task_type))
                if not task:
                    collection = self.prop(self.task_types, '%s.data.collection' % task_type)
                    msg = '您曾领取过该%s的校对或审定任务，不可以重复领取' % ('页编码' if collection == 'page' else '聚类字种')
                    return self.send_error_response(e.no_task_to_pick, message=task_id and msg)
                r = self.db.task.update_one({'_id': task['_id'], 'status': self.STATUS_PUBLISHED}, {'$set': {
                    'status': self.STATUS_PICKED, 'picked_user_id': self.user_id, 'picked_by': self.username,
                    'picked_time': self.now(), 'updated_time': self.now()
                }})
                if r.matched_count:  # 分配成功
                    url = '/task/do/%s/%s' % (task['task_type'], task['_id'])
                    self.send_data_response({'url': url, 'doc_id': task.get('doc_id'), 'task_id': task['_id']})
                    self.update_page_status(self.STATUS_PICKED, task)
                    return
                else:  # 重新分配
                    task = None

        except self.DbError as error:
            return self.send_db_error(error)

    def pick_one(self, task_type, batch):
        cond = {'task_type': task_type, 'status': self.STATUS_PUBLISHED}
        # 不可以重复领取同组任务
        self.has_num(task_type) and cond.update({'group_task_users': {'$ne': self.user_id}})
        # 设置批次号
        if not batch:
            cond.update({'is_oriented': None})
        elif ',' in batch:
            cond.update({'batch': {'$in': [b.strip() for b in batch.split(',')]}})
        else:
            cond.update({'batch': batch})
        return self.db.task.find_one(cond, sort=[('priority', 1)])


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_id'

    def post(self, task_id):
        """退回任务"""
        try:
            if self.task['picked_user_id'] != self.user_id:
                return self.send_error_response(e.task_unauthorized, message='您没有该任务的权限')
            if self.task['status'] != self.STATUS_PICKED:
                return self.send_error_response(e.task_status_error, message='只能退回进行中的任务')
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
        """批量更新任务批次或管理备注"""
        try:
            rules = [(v.not_both_empty, '_ids', '_id')]
            field == 'batch' and rules.append((v.not_empty, 'batch'))
            field == 'remark' and rules.append((v.not_none, 'remark'))
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


class UpdateTaskMyRemarkApi(TaskHandler):
    URL = '/api/task/my_remark/@task_id'

    def post(self, task_id):
        """更新我的备注"""
        try:
            rules = [(v.not_none, 'my_remark')]
            self.validate(self.data, rules)

            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                return self.send_error_response(e.no_object, message="没有找到任务%s" % task_id)
            if task['picked_user_id'] != self.user_id:
                return self.send_error_response(e.task_unauthorized)
            self.db.task.update_one({'_id': task['_id']}, {'$set': {'my_remark': self.data['my_remark']}})
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class RepublishTaskApi(TaskHandler):
    URL = ['/api/task/republish', '/api/task/republish/@task_id']

    def post(self, task_id=None):
        """重新发布任务"""
        try:
            ids = [task_id] if task_id else self.data['ids']
            if not ids:
                return self.send_error_response(e.no_object, message='没有指定任务id参数')
            project = {'status': 1, 'task_type': 1, 'doc_id': 1}
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(i) for i in ids]}}, project))
            if not tasks:
                return self.send_error_response(e.no_object, message='没有找到任务')
            statuses = [self.STATUS_PICKED, self.STATUS_FAILED, self.STATUS_RETURNED]
            if not [t for t in tasks if t.get('status') in statuses]:
                return self.send_error_response(e.task_status_error, message='只能重新发布进行中、退回或失败的任务')

            task_ids = [t['_id'] for t in tasks if t['status'] in statuses]
            un_fields = ['steps.submitted', 'picked_user_id', 'picked_by', 'picked_time', 'return_reason', 'message']
            r = self.db.task.update_many(
                {'_id': {'$in': task_ids}, 'status': {'$in': statuses}},
                {'$set': {'status': self.STATUS_PUBLISHED, 'result': {}}, '$unset': {k: '' for k in un_fields}}
            )
            if task_id:
                self.update_page_status(self.STATUS_PUBLISHED)
            content = dict(task_type=tasks[0]['task_type'], doc_id=tasks[0].get('doc_id') or '')
            self.add_log('republish_task', target_id=task_ids, content=content, remark='%d tasks' % r.modified_count)

            return self.send_data_response(published_count=r.modified_count)

        except self.DbError as error:
            return self.send_db_error(error)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete'

    def post(self):
        """删除任务(只能删除已发布未领取、已获取、等待前置任务、已退回的任务)"""
        try:
            rules = [(v.not_both_empty, '_ids', '_id')]
            self.validate(self.data, rules)

            _ids = self.data['_ids'] if self.data.get('_ids') else [self.data['_id']]
            status = [self.STATUS_PUBLISHED, self.STATUS_FETCHED, self.STATUS_PENDING, self.STATUS_RETURNED]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in _ids]}, 'status': {'$in': status}}))
            r = self.db.task.delete_many({'_id': {'$in': [t['_id'] for t in tasks]}})
            self.add_log('delete_task', target_id=[t['_id'] for t in tasks])

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
        @param tasks, 格式为 [[_id, task_type, doc_id], ]
        @return dict, 如{'un_existed':[], 'un_published':[], 'lock_failed':[], 'assigned':[]}
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
        """完成任务，供测试用例使用"""
        try:
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()}})
            self.update_post_tasks(self.task)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class InitTasksForOPTestApi(TaskHandler):
    URL = '/api/task/init4op'

    def post(self):
        """初始化数据处理任务，以便OP平台进行测试。注意：该API仅仅是配合OP平台测试使用"""
        try:
            rules = [(v.not_empty, 'page_names', 'import_dirs', 'layout')]
            self.validate(self.data, rules)

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


class PageTaskStatisticApi(TaskHandler):
    URL = '/api/task/statistic/@page_task'

    def post(self, task_type):
        """统计页任务数据"""
        try:
            query = self.data.get('query') or ''
            cond = query and self.get_task_search_condition(query)[0] or {}
            cond.update({'task_type': task_type, 'status': {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]},
                         'picked_user_id': self.user_id})
            counts = list(self.db.task.aggregate([{'$match': cond}, {'$group': {
                '_id': None, 'char_count': {'$sum': '$char_count'}, 'added': {'$sum': '$added'},
                'deleted': {'$sum': '$deleted'}, 'changed': {'$sum': '$changed'},
                'used_time': {'$sum': '$used_time'},
            }}]))
            ret = counts and counts[0] or {}
            return self.send_data_response(ret)

        except self.DbError as error:
            return self.send_db_error(error)
