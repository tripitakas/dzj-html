#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
import json
from datetime import datetime
from controller import errors
from controller.base import DbError
from controller import errors as e
from controller import validate as v
from controller.task.base import TaskHandler
from controller.auth import can_access, get_all_roles
from controller.task.publish import PublishBaseHandler
from .view import TaskLobbyHandler as Lobby
from bson.objectid import ObjectId


class GetReadyTasksApi(TaskHandler):
    URL = '/api/task/ready/@task_type'

    def post(self, task_type):
        """ 获取数据已就绪的任务列表
        已就绪有两种情况：1. 任务不依赖任何数据；2. 任务依赖的数据已就绪
        """
        assert task_type in self.task_types
        try:
            data = self.get_request_data()
            doc_filter = dict()
            if data.get('prefix'):
                doc_filter.update({'$regex': '.*%s.*' % data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                doc_filter.update({'$nin': data.get('exclude')})
            collection, id_name, input_field, shared_field = self.get_task_data_conf(task_type)
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
            response = {'docs': [d[id_name] for d in list(docs)], 'page_size': page_size,
                        'page_no': page_no, 'total_count': count}
            return self.send_data_response(response)
        except DbError as error:
            return self.send_db_error(error)


class PublishTasksApi(PublishBaseHandler):
    URL = r'/api/task/publish'

    def get_doc_ids(self, data):
        doc_ids = data.get('doc_ids') or []
        if not doc_ids:
            ids_file = self.request.files.get('ids_file')
            if ids_file:
                ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
                try:
                    doc_ids = json.loads(ids_str)
                except json.decoder.JSONDecodeError:
                    ids_str = re.sub(r'\n+', '|', ids_str)
                    doc_ids = ids_str.split(r'|')
            elif data.get('prefix'):
                collection, id_name, input_field, shared_field = self.get_task_data_conf(data['task_type'])
                condition = {id_name: {'$regex': '.*%s.*' % data['prefix'], '$options': '$i'}}
                if input_field:
                    condition[input_field] = {"$nin": [None, '']}
                doc_ids = [doc.get(id_name) for doc in self.db[collection].find(condition)]
        return doc_ids

    def post(self):
        """ 根据数据id发布任务。
        @param task_type 任务类型
        @param steps list，步骤
        @param pre_tasks list，前置任务
        @param doc_ids str，待发布任务的名称
        @param priority str，1/2/3，数字越大优先级越高
        """
        data = self.get_request_data()
        if data.get('task_type') == 'import_image':
            return self.publish_import_image()

        data['doc_ids'] = self.get_doc_ids(data)
        assert isinstance(data['doc_ids'], list)
        rules = [
            (v.not_empty, 'doc_ids', 'task_type', 'priority', 'force'),
            (v.is_priority, 'priority'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
        ]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        try:
            max_count = self.MAX_PUBLISH_RECORDS
            if len(data['doc_ids']) > max_count:
                return self.send_error_response(e.task_count_exceed_max, message='任务数量不能超过%s' % max_count)
            log = self.publish_many(data['task_type'], data.get('pre_tasks', []), data.get('steps', []),
                                    data['priority'], data['force'] == '是', doc_ids=data['doc_ids'])
            return self.send_data_response({k: value for k, value in log.items() if value})

        except DbError as error:
            return self.send_db_error(error)

    def publish_import_image(self):
        """ 发布图片导入任务"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'import_dir', 'redo', 'layout')]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            data['redo'] = data['redo'] == '是'
            now, status = datetime.now(), self.STATUS_OPENED
            param = {k: data.get(k) for k in ['pan_name', 'import_dir', 'layout', 'redo', 'layout']}
            task = dict(task_type='import_image', collection=None, id_name=None, doc_id=None, status=status,
                        priority=1, steps=None, pre_tasks=None, input=param, result={},
                        create_time=now, updated_time=now, publish_time=now,
                        publish_user_id=self.current_user['_id'],
                        publish_by=self.current_user['name'])
            r = self.db.task.insert_one(task)
            if r.inserted_id:
                self.send_data_response(dict(_id=r.inserted_id))
                self.add_op_log('publish_import_image', context='%s,%s' % (data['import_dir'], data['redo']),
                                target_id=r.inserted_id)

        except DbError as error:
            return self.send_db_error(error)


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type):
        """ 领取任务。
        :param task_type: 任务类型。如果是组任务，针对同一份数据，只能领取组任务中的一个。
        """
        try:
            now, user_id, user_name = datetime.now(), self.current_user['_id'], self.current_user['name']
            # 检查是否有未完成的任务
            task_type = 'text_proof' if 'text_proof' in task_type else task_type
            task_meta = self.get_task_meta(task_type)
            task_filter = {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type
            condition = {'task_type': task_filter, 'status': self.STATUS_PICKED, 'picked_user_id': user_id}
            uncompleted = self.db.task.find_one(condition)
            if uncompleted:
                url = '/task/do/%s/%s' % (task_type, uncompleted['_id'])
                return self.send_error_response(e.task_uncompleted, **{'url': url, 'doc_id': uncompleted['doc_id']})

            task_id, task = self.prop(self.get_request_data(), 'task_id'), None
            if task_id:
                task = self.db.task.find_one({'_id': ObjectId(task_id)})
                if not task:
                    return self.send_error_response(e.no_object, message='没有找到该任务')
                if task['status'] != self.STATUS_OPENED:
                    return self.send_error_response(e.task_not_published)
            else:  # 如果task_id为空，则从任务大厅任取一个
                tasks = Lobby.get_lobby_tasks_by_type(self, task_type, page_size=1)[0]
                if not tasks:
                    return self.send_error_response(errors.no_task_to_pick)
                else:
                    task = tasks[0]

            # 如果任务为组任务，则检查用户是否曾领取过该组任务
            if task_meta.get('groups') and self.db.task.find_one(dict(
                    task_type=task_filter, collection=task['collection'], id_name=task['id_name'],
                    doc_id=task['doc_id'], picked_user_id=user_id
            )):
                message = '您曾领取过本页面组任务中的一个，不能再领取其它任务'
                return self.send_error_response(e.group_task_duplicated, message=message)

            # 如果任务有共享数据，则尝试分配数据锁
            shared_field = self.get_shared_field(task_type)
            if shared_field:
                r = self.assign_task_lock(task['doc_id'], shared_field, task_type)
                if r is not True:
                    return self.send_error_response(r)

            # 分配任务给当前用户
            self.db.task.update_one({'_id': task['_id']}, {'$set': {
                'status': self.STATUS_PICKED, 'picked_user_id': user_id, 'picked_by': user_name,
                'picked_time': now, 'updated_time': now,
            }})

            self.add_op_log('pick_' + task_type, context=task['doc_id'], target_id=task['_id'])
            url = '/task/do/%s/%s' % (task_type, task['_id'])
            return self.send_data_response({'url': url, 'doc_id': task['doc_id'], 'task_id': task['_id']})

        except DbError as error:
            return self.send_db_error(error)


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_type/@task_id'

    def post(self, task_type, task_id):
        """ 用户退回任务 """
        try:
            now, user_id = datetime.now(), self.current_user['_id']
            task = self.db.task.find_one({'_id': ObjectId(task_id), 'picked_user_id': user_id})
            if not task:
                return self.send_error_response(errors.no_object, message='没有找到该任务')

            # 退回任务
            reason = self.prop(self.get_request_data(), 'reason', '')
            update = {'status': self.STATUS_RETURNED, 'updated_time': now, 'message': reason}
            r = self.db.task.update_one({'_id': task['_id']}, {'$set': update})
            if r.matched_count:
                self.add_op_log('return_' + task_type, context=task_id, target_id=task['_id'])

            # 释放数据锁
            self.release_task_lock(task)

            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class RepublishTaskApi(TaskHandler):
    URL = '/api/task/republish/@task_id'

    def post(self, task_id):
        """ 管理员重新发布进行中的任务 """
        try:
            # 检查参数
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(e.no_object, message='没有找到该任务')
            if task.get('status') not in [self.STATUS_PICKED, self.STATUS_FAILED]:
                self.send_error_response(e.republish_only_picked_or_failed, message='只能重新发布进行中或失败的任务')

            # 重新发布
            pre_tasks = {k: '' for k in self.prop(task, 'pre_tasks', [])}
            update = {'status': self.STATUS_OPENED, 'pre_tasks': pre_tasks, 'result': {}}
            unset = {'steps.submitted': '', 'picked_user_id': '', 'picked_by': '', 'picked_time': ''}
            self.db.task.update_one({'_id': task['_id']}, {'$set': update})
            self.db.task.update_one({'_id': task['_id']}, {'$unset': unset})
            self.add_op_log('republish', target_id=task['_id'], context=task['task_type'])

            # 释放数据锁
            self.release_task_lock(task)

            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete/@task_type'

    def post(self, task_type):
        """ 删除任务(只能删除那些未占有数据锁的任务，包括已发布未领取、等待前置任务、已退回等)"""
        assert task_type in self.all_task_types()
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_ids', '_id')]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            # 删除任务
            _ids = data['_ids'] if data.get('_ids') else [data['_id']]
            status = [self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_RETURNED]
            r = self.db.task.delete_many({'_id': {'$in': [ObjectId(t) for t in _ids]}, 'status': {'$in': status}})
            self.add_op_log('delete_' + task_type, context=_ids)
            return self.send_data_response({'count': r.deleted_count})

        except DbError as error:
            return self.send_db_error(error)


class AssignTasksApi(TaskHandler):
    URL = '/api/task/assign/@task_type'

    @staticmethod
    def can_user_access_task(task_type, user):
        user_roles = ','.join(get_all_roles(user.get('roles')))
        return can_access(user_roles, '/api/task/pick/%s' % task_type, 'POST')

    def post(self, task_type):
        """ 批量指派已发布的任务给某用户
        :return dict, 如{'un_existed':[], 'un_published':[], 'lock_failed':[], 'assigned':[]}
        """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'task_ids', 'user_id')]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            user = self.db.user.find_one({'_id': ObjectId(data['user_id'])})
            if not user:
                return self.send_error_response(e.no_user)

            # 检查用户权限（管理员指派任务时，仅检查用户角色）
            if not self.can_user_access_task(task_type, user):
                return self.send_error_response(e.task_unauthorized, message='用户没有该任务的权限')

            # 批量指派已发布的任务
            log, lock_failed, assigned = dict(), [], []
            shared_field = self.get_shared_field(task_type)
            now, user_id, user_name = datetime.now(), user['_id'], user['name']
            tasks = list(self.db.task.find({'_id': {'$in': [ObjectId(t) for t in data['task_ids']]}}))
            log['un_existed'] = set(data['task_ids']) - set([str(t['_id']) for t in tasks])
            log['un_published'] = [t['doc_id'] for t in tasks if t['status'] != self.STATUS_OPENED]
            opened_tasks = [t for t in tasks if t['status'] == self.STATUS_OPENED]
            for task in opened_tasks:
                # 尝试分配数据锁
                if shared_field and task.get('doc_id'):
                    r = self.assign_task_lock(task['doc_id'], shared_field, task_type)
                    if r is not True:
                        lock_failed.append(task['doc_id'] + ':' + r[1])
                        continue
                # 分配任务
                self.db.task.update_one({'_id': task['_id']}, {'$set': {
                    'status': self.STATUS_PICKED, 'picked_user_id': user_id, 'picked_by': user_name,
                    'picked_time': now, 'updated_time': now,
                }})
                assigned.append(task['doc_id'])
            log['lock_failed'] = lock_failed
            log['assigned'] = assigned
            self.add_op_log('assign_' + task_type, context='%s, %s' % (user_id, assigned))
            log = {k: v for k, v in log.items() if v}
            return self.send_data_response(log)

        except DbError as error:
            return self.send_db_error(error)


class FinishTaskApi(TaskHandler):
    URL = '/api/task/finish/@task_type/@task_id'

    def post(self, task_type, task_id):
        """ 提交任务，释放数据锁，并且更新后置任务状态。"""
        try:
            task = self.db.task.find_one({'task_type': task_type, '_id': ObjectId(task_id)})
            if not task:
                return self.send_error_response(errors.no_object)
            self.finish_task(task)
            return self.send_data_response()
        except DbError as error:
            return self.send_db_error(error)


class LockTaskDataApi(TaskHandler):
    URL = '/api/data/lock/@shared_field/@doc_id'

    def post(self, shared_field, doc_id):
        """ 获取临时数据锁。"""
        assert shared_field in self.data_auth_maps
        try:
            r = self.assign_temp_lock(doc_id, shared_field)
            if r is True:
                return self.send_data_response()
            else:
                return self.send_error_response(r)

        except DbError as error:
            return self.send_db_error(error)


class UnlockTaskDataApi(TaskHandler):
    URL = '/api/data/unlock/@shared_field/@doc_id'

    def post(self, shared_field, doc_id):
        """ 释放临时数据锁。"""
        assert shared_field in self.data_auth_maps
        try:
            count = self.release_temp_lock(doc_id, shared_field)
            return self.send_data_response(dict(count=count))

        except DbError as error:
            return self.send_db_error(error)


class InitTasksForTestApi(TaskHandler):
    URL = '/api/task/init_for_test'

    def post(self):
        """ 初始化数据处理任务，以便OP平台进行测试。
        注意：该API仅仅是配合OP平台测试使用"""
        data = self.get_request_data()
        rules = [(v.not_empty, 'page_names', 'import_dirs', 'layout')]
        errs = v.validate(data, rules)
        if errs:
            return self.send_error_response(errs)

        try:
            tasks, now = [], datetime.now()
            meta = dict(task_type='import_image', collection=None, id_name=None, doc_id=None, status='opened',
                        priority=1, steps=None, pre_tasks=None, input=None, result={},
                        create_time=now, updated_time=now, publish_time=now,
                        publish_user_id=self.current_user['_id'],
                        publish_by=self.current_user['name'])

            # 清空数据处理任务
            self.db.task.delete_many({'task_type': {'$in': ['import_image', 'ocr_box', 'ocr_text', 'upload_cloud']}})

            # 创建导入图片任务
            for import_dir in data['import_dirs']:
                task = meta.copy()
                task.update(dict(task_type='import_image', status='opened', input=dict(
                    import_dir=import_dir, redo=True, layout=data['layout'])))
                tasks.append(task)

            # 创建其它类型的任务
            for task_type in ['ocr_box', 'ocr_text', 'upload_cloud']:
                for page_name in data['page_names']:
                    task = meta.copy()
                    task.update(dict(task_type=task_type, status='opened', collection='page', doc_id=page_name))
                    if task_type == 'ocr_text':
                        page = self.db.page.find_one({'name': page_name})
                        if page:
                            task['input'] = {k: page[k] for k in ['blocks', 'columns', 'chars']}
                    tasks.append(task)

            self.db.task.insert_many(tasks)

            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)
