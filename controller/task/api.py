#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
import json
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors as e
from controller.base import DbError
from controller import validate as v
from controller.helper import get_url_param
from controller.task.base import TaskHandler
from controller.data.view import DataPageHandler
from controller.auth import can_access, get_all_roles
from controller.task.publish import PublishBaseHandler


class GetReadyDocsApi(TaskHandler):
    URL = '/api/task/ready/@task_type'

    def post(self, task_type):
        """ 获取数据已就绪的任务列表。已就绪有两种情况：1. 任务不依赖任何数据；2. 任务依赖的数据已就绪"""
        try:
            assert task_type in self.task_types
            data = self.get_request_data()
            doc_filter = dict()
            if data.get('prefix'):
                doc_filter.update({'$regex': data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                doc_filter.update({'$nin': data.get('exclude')})
            collection, id_name, input_field, shared_field = self.get_data_conf(task_type)
            output_field = self.prop(self.task_types, '%s.data.output_field' % task_type)
            condition = {id_name: doc_filter} if doc_filter else {}
            if input_field:
                condition.update({input_field: {'$nin': [None, '']}})  # 任务所依赖的数据字段存在且不为空
            if output_field:
                condition.update({output_field: {'$in': [None, '']}})  # 任务字段为空，则表示任务未完成
            page_no = int(data.get('page', 0)) if int(data.get('page', 0)) > 1 else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db[collection].count_documents(condition)
            docs = self.db[collection].find(condition).limit(page_size).skip(page_size * (page_no - 1))
            doc_ids = [d[id_name] for d in list(docs)]
            response = {'docs': doc_ids, 'page_size': page_size, 'page_no': page_no, 'total_count': count}
            return self.send_data_response(response)

        except DbError as error:
            return self.send_db_error(error)


class PublishDocTasksApi(PublishBaseHandler):
    URL = r'/api/task/publish/(page)'

    def post(self, collection):
        """ 发布任务"""
        data = self.get_request_data()
        data['doc_ids'] = self.get_doc_ids(data)
        assert isinstance(data['doc_ids'], list)
        rules = [
            (v.not_empty, 'doc_ids', 'task_type', 'priority', 'force', 'batch'),
            (v.is_priority, 'priority'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
        ]
        self.validate(data, rules)

        try:
            if len(data['doc_ids']) > self.MAX_PUBLISH_RECORDS:
                message = '任务数量不能超过%s' % self.MAX_PUBLISH_RECORDS
                return self.send_error_response(e.task_count_exceed, message=message)
            log = self.publish_many(
                data['task_type'], data.get('pre_tasks', []), data.get('steps', []), data['priority'],
                data['force'] == '是', data['doc_ids'], data['batch']
            )
            return self.send_data_response({k: value for k, value in log.items() if value})

        except DbError as error:
            return self.send_db_error(error)

    def get_doc_ids(self, data):
        """ 获取页码。有四种方式：页编码、文件、前缀、检索参数"""
        doc_ids = data.get('doc_ids') or []
        if doc_ids:
            return doc_ids
        ids_file = self.request.files.get('ids_file')
        collection, id_name, input_field, shared_field = self.get_data_conf(data['task_type'])
        if ids_file:
            ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
            try:
                doc_ids = json.loads(ids_str)
            except json.decoder.JSONDecodeError:
                ids_str = re.sub(r'\n+', '|', ids_str)
                doc_ids = ids_str.split(r'|')
        elif data.get('prefix'):
            condition = {id_name: {'$regex': data['prefix'], '$options': '$i'}}
            if input_field:
                condition[input_field] = {"$nin": [None, '']}
            doc_ids = [doc.get(id_name) for doc in self.db[collection].find(condition)]
        elif data.get('search'):
            condition = DataPageHandler.get_page_search_condition(data['search'])[0]
            query = self.db[collection].find(condition)
            page = get_url_param('page', data['search'])
            if page:
                size = get_url_param('page_size', data['search']) or self.prop(self.config, 'pager.page_size', 10)
                query = query.skip((int(page) - 1) * int(size)).limit(int(size))
            doc_ids = [doc.get(id_name) for doc in list(query)]
        return doc_ids


class PublishImageTasksApi(TaskHandler):
    URL = r'/api/task/publish/import'

    def post(self):
        """ 发布图片导入任务"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'source', 'import_dir', 'priority', 'redo', 'layout')]
            self.validate(data, rules)

            task = self.get_publish_meta('import_image')
            priority, status = int(data['priority']), self.STATUS_PUBLISHED
            param = {k: data.get(k) for k in ['source', 'pan_name', 'import_dir', 'layout', 'redo']}
            task.update(dict(status=status, priority=priority, input=param))
            r = self.db.task.insert_one(task)
            message = '%s, %s,%s' % ('import_image', data['import_dir'], data['redo'])
            self.add_op_log('publish_task', target_id=r.inserted_id, context=message)
            self.send_data_response(dict(_id=r.inserted_id))

        except DbError as error:
            return self.send_db_error(error)


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type):
        """ 领取任务"""
        try:
            now, user_id, user_name = datetime.now(), self.current_user['_id'], self.current_user['name']
            # 检查是否有未完成的任务
            task_type = 'text_proof' if 'text_proof' in task_type else task_type
            task_filter = {'$regex': task_type} if self.is_group(task_type) else task_type
            uncompleted = self.find_mine(task_type=task_type, status=self.STATUS_PICKED, page_size=1)
            if uncompleted:
                url = '/task/do/%s/%s' % (uncompleted[0]['task_type'], uncompleted[0]['_id'])
                return self.send_error_response(e.task_uncompleted, **{'url': url, 'doc_id': uncompleted[0]['doc_id']})

            task_id, task = self.prop(self.get_request_data(), 'task_id'), None
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
                    task_type=task_filter, collection=task['collection'], id_name=task['id_name'],
                    doc_id=task['doc_id'], picked_user_id=user_id
            )):
                message = '您曾领取过本页面组任务中的一个，不能再领取其它任务'
                return self.send_error_response(e.group_task_duplicated, message=message)
            # 分配数据锁
            r = self.assign_task_lock(task['doc_id'], task_type, self.current_user)
            if isinstance(r, tuple):
                return self.send_error_response(r)
            # 分配任务
            self.db.task.update_one({'_id': task['_id']}, {'$set': {
                'status': self.STATUS_PICKED, 'picked_user_id': user_id, 'picked_by': user_name,
                'picked_time': now, 'updated_time': now,
            }})
            self.add_op_log('pick_task', target_id=task['_id'], context=task['task_type'])
            # 更新doc
            self.update_doc(task, self.STATUS_PICKED)
            # 设置返回参数
            url = '/task/do/%s/%s' % (task['task_type'], task['_id'])
            return self.send_data_response({'url': url, 'doc_id': task['doc_id'], 'task_id': task['_id']})

        except DbError as error:
            return self.send_db_error(error)


class UpdateTaskApi(TaskHandler):
    URL = '/api/task/(batch|remark)'

    def post(self, field):
        """ 批量更新任务批次或备注"""
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_ids', '_id'), (v.not_both_empty, 'batch', 'remark')]
            self.validate(data, rules)

            update = {field: data[field]}
            if data.get('_id'):
                if data.get('is_sample'):
                    update['is_sample'] = True if data['is_sample'] == '是' else False
                r = self.db.task.update_one({'_id': ObjectId(data['_id'])}, {'$set': update})
                self.add_op_log('update_task', target_id=data['_id'], context=data[field])
            else:
                _ids = [ObjectId(t) for t in data['_ids']]
                r = self.db.task.update_many({'_id': {'$in': _ids}}, {'$set': update})
                self.add_op_log('update_task', target_id=_ids, context=data[field])
            self.send_data_response(dict(count=r.matched_count))

        except DbError as error:
            return self.send_db_error(error)


class StatisticTaskApi(TaskHandler):
    URL = '/api/task/statistic'

    def post(self):
        """ 统计任务"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'kind', 'search')]
            self.validate(data, rules)

        except DbError as error:
            return self.send_db_error(error)


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_id'

    def post(self, task_id):
        """ 退回任务 """
        try:
            if self.task['picked_user_id'] != self.current_user['_id']:
                return self.send_error_response(e.unauthorized, message='您没有该任务的权限')
            reason = self.prop(self.get_request_data(), 'reason', '')
            update = {'status': self.STATUS_RETURNED, 'updated_time': datetime.now(), 'return_reason': reason}
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
            self.add_op_log('return_task', target_id=self.task['_id'])
            self.release_task_lock(self.task, self.current_user)
            self.update_doc(self.task, self.STATUS_RETURNED)
            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class RepublishTaskApi(TaskHandler):
    URL = '/api/task/republish/@task_id'

    def post(self, task_id):
        """ 重新发布任务"""
        try:
            if self.task.get('status') not in [self.STATUS_PICKED, self.STATUS_FAILED]:
                self.send_error_response(e.republish_only_picked_or_failed, message='只能重新发布进行中或失败的任务')
            # 重新发布
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'pre_tasks': {k: '' for k in self.prop(self.task, 'pre_tasks', [])},
                'status': self.STATUS_PUBLISHED, 'result': {}
            }})
            unset = ['steps.submitted', 'picked_user_id', 'picked_by', 'picked_time', 'return_reason']
            self.db.task.update_one({'_id': self.task['_id']}, {'$unset': {k: '' for k in unset}})
            self.add_op_log('republish_task', target_id=self.task['_id'])
            # 释放数据锁
            self.release_task_lock(self.task, self.current_user)
            # 更新doc
            self.update_doc(self.task, self.STATUS_PUBLISHED)
            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete'

    def post(self):
        """ 删除任务(只能删除已发布未领取、等待前置任务、已退回的任务，这些任务未占数据锁)"""
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_ids', '_id')]
            self.validate(data, rules)

            _ids = data['_ids'] if data.get('_ids') else [data['_id']]
            status = [self.STATUS_PUBLISHED, self.STATUS_PENDING, self.STATUS_RETURNED]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in _ids]}, 'status': {'$in': status}}))
            r = self.db.task.delete_many({'_id': {'$in': [t['_id'] for t in tasks]}})
            self.add_op_log('delete_task', target_id=_ids)
            # 更新doc
            for task in tasks:
                self.update_doc(task)
            return self.send_data_response({'count': r.deleted_count})

        except DbError as error:
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
            data = self.get_request_data()
            rules = [(v.not_empty, 'tasks', 'user_id')]
            self.validate(data, rules)
            user = self.db.user.find_one({'_id': ObjectId(data['user_id'])})
            if not user:
                return self.send_error_response(e.no_user)

            log, lock_failed, assigned = dict(), [], []
            now, user_id, user_name = datetime.now(), user['_id'], user['name']
            # 去掉用户无权访问的任务
            log['unauthorized'] = [t[2] for t in data['tasks'] if not self.can_user_access(t[1], user)]
            authorized = [t[0] for t in data['tasks'] if self.can_user_access(t[1], user)]
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in authorized]}}))
            # 去掉不存在的任务
            log['un_existed'] = set(authorized) - set([str(t['_id']) for t in tasks])
            # 去掉未发布的任务
            log['un_published'] = [t['doc_id'] for t in tasks if t['status'] != self.STATUS_PUBLISHED]
            published = [t for t in tasks if t['status'] == self.STATUS_PUBLISHED]
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
                self.update_doc(task, self.STATUS_PICKED)

            log['lock_failed'] = lock_failed
            log['assigned'] = assigned
            self.add_op_log('assign_task', context='%s, %s' % (user_id, assigned))
            self.send_data_response({k: v for k, v in log.items() if v})

        except DbError as error:
            return self.send_db_error(error)


class FinishTaskApi(TaskHandler):
    URL = '/api/task/finish/@task_id'

    def post(self, task_id):
        """ 提交任务，释放数据锁，并且更新后置任务状态"""
        try:
            self.finish_task(self.task)
            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class LockTaskApi(TaskHandler):
    URL = '/api/data/lock/@shared_field/@doc_id'

    def post(self, shared_field, doc_id):
        """ 获取临时数据锁"""
        assert shared_field in self.data_auth_maps
        try:
            r = self.assign_temp_lock(doc_id, shared_field, self.current_user)
            if r is True:
                return self.send_data_response()
            else:
                return self.send_error_response(r)

        except DbError as error:
            return self.send_db_error(error)


class UnlockTaskApi(TaskHandler):
    URL = ['/api/data/admin/unlock/@shared_field/@doc_id',
           '/api/data/unlock/@shared_field/@doc_id']

    def post(self, shared_field, doc_id):
        """ 释放临时数据锁"""
        assert shared_field in self.data_auth_maps
        try:
            count = self.release_temp_lock(doc_id, shared_field)
            return self.send_data_response(dict(count=count))

        except DbError as error:
            return self.send_db_error(error)


class InitTestTasksApi(TaskHandler):
    URL = '/api/task/init'

    def post(self):
        """ 初始化数据处理任务，以便OP平台进行测试。注意：该API仅仅是配合OP平台测试使用"""
        data = self.get_request_data()
        rules = [(v.not_empty, 'page_names', 'import_dirs', 'layout')]
        self.validate(data, rules)

        try:
            tasks, task_types = [], ['import_image', 'ocr_box', 'ocr_text', 'upload_cloud']
            # 清空数据处理任务
            self.db.task.delete_many({'task_type': {'$in': task_types}})
            # 创建导入图片任务
            for import_dir in data['import_dirs']:
                task = self.get_publish_meta('import_image')
                params = dict(import_dir=import_dir, redo=True, layout=data['layout'], batch='测试批次')
                task.update(dict(task_type='import_image', status='published', input=params))
                tasks.append(task)
            # 创建其它类型的任务
            for task_type in ['ocr_box', 'ocr_text', 'upload_cloud']:
                for page_name in data['page_names']:
                    task = self.get_publish_meta(task_type)
                    task.update(dict(task_type=task_type, status='published', collection='page', doc_id=page_name))
                    if task_type == 'ocr_text':
                        page = self.db.page.find_one({'name': page_name})
                        if page:
                            task['input'] = {k: page[k] for k in ['blocks', 'columns', 'chars']}
                    tasks.append(task)
            r = self.db.task.insert_many(tasks)
            if r.inserted_ids:
                self.send_data_response(dict(ids=r.inserted_ids))

        except DbError as error:
            return self.send_db_error(error)
