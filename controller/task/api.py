#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors
import controller.errors as e
import controller.validate as v
from controller.base import DbError
from controller.task.base import TaskHandler
from controller.auth import can_access, get_all_roles
from controller.task.publish import PublishBaseHandler
from .view import TaskLobbyHandler as Lobby


class GetReadyTasksApi(TaskHandler):
    URL = '/api/task/ready/@task_type'

    def post(self, task_type):
        """ 获取数据已就绪的任务列表
        已就绪有两种情况：1. 任务不依赖任何数据；2. 任务依赖的数据已就绪
        """
        assert task_type in self.task_types
        try:
            data = self.get_request_data()
            collection, id_name, input_field, shared_field = self.get_task_meta(task_type)
            doc_filter = dict()
            if data.get('prefix'):
                doc_filter.update({'$regex': '.*%s.*' % data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                doc_filter.update({'$nin': data.get('exclude')})
            condition = {id_name: doc_filter} if doc_filter else {}
            if input_field:
                condition.update({input_field: {'$nin': [None, '']}})  # 任务所依赖的数据字段存在且不为空
            page_no = int(data.get('page', 0)) if int(data.get('page', 0)) > 1 else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db[collection].count_documents(condition)
            docs = self.db[collection].find(condition).limit(page_size).skip(page_size * (page_no - 1))
            response = {'docs': [d[id_name] for d in list(docs)], 'page_size': page_size,
                        'page_no': page_no, 'total_count': count}
            return self.send_data_response(response)
        except DbError as err:
            return self.send_db_error(err)


class PublishTasksApi(PublishBaseHandler):
    URL = r'/api/task/publish'

    def get_doc_ids(self, data):
        doc_ids = data.get('doc_ids')
        if not doc_ids:
            ids_file = self.request.files.get('ids_file')
            if ids_file:
                ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
                ids_str = re.sub(r'\n+', '|', ids_str)
                doc_ids = ids_str.split(r'|')
            elif data.get('prefix'):
                collection, id_name, input_field, shared_field = self.get_task_meta(data['task_type'])
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
        data['doc_ids'] = self.get_doc_ids(data)
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
            assert isinstance(data['doc_ids'], list)
            if len(data['doc_ids']) > self.MAX_PUBLISH_RECORDS:
                return self.send_error_response(e.task_exceed_max, message='任务数量不能超过%s' % self.MAX_PUBLISH_RECORDS)

            force = data['force'] == '1'
            log = self.publish_task(data['task_type'], data.get('pre_tasks', []), data.get('steps', []),
                                    data['priority'], force, doc_ids=data['doc_ids'])
            return self.send_data_response({k: value for k, value in log.items() if value})

        except DbError as err:
            return self.send_db_error(err)


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type):
        """ 领取任务。
        :param task_type: 任务类型。如果是组任务，用户只能领取一份数据的一组任务中的一个。
        """
        try:
            # 检查是否有未完成的任务
            task_meta = self.all_task_types()[task_type]
            task_type_filter = {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type
            condition = {
                'task_type': task_type_filter,
                'picked_user_id': self.current_user['_id'],
                'status': self.STATUS_PICKED,
            }
            uncompleted = self.db.task.find_one(condition)
            if uncompleted:
                url = '/task/do/%s/%s' % (uncompleted['task_type'], uncompleted['_id'])
                return self.send_error_response(
                    e.task_uncompleted, **{'doc_id': uncompleted['doc_id'], 'url': url}
                )

            # 如果_id为空，则任取一个任务
            task_id = self.get_request_data().get('task_id')
            if not task_id:
                tasks = Lobby.get_lobby_tasks_by_type(self, task_type, page_size=1)[0]
                if not tasks:
                    return self.send_error_response(errors.no_task_to_pick)
                return self.assign_task(tasks[0])

            # 检查任务及任务状态
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                return self.send_error_response(e.no_object)
            if task['status'] != self.STATUS_OPENED:
                return self.send_error_response(e.task_not_published)

            # 如果任务有共享数据，则检查对应的数据是否被锁定
            shared_field = self.get_shared_field(task_type)
            if shared_field and shared_field in self.data_auth_maps:
                if self.is_data_locked(task['doc_id'], shared_field):
                    return self.send_error_response(e.data_is_locked)

            # 如果任务为组任务，则检查用户是否曾领取过该组任务
            condition = dict(task_type=task_type_filter, collection=task['collection'], id_name=task['id_name'],
                             doc_id=task['doc_id'], picked_user_id=self.current_user['_id'])
            if task_meta.get('groups') and self.db.task.find_one(condition):
                return self.send_error_response(e.group_task_duplicated)

            # 分配任务及数据锁
            return self.assign_task(task)

        except DbError as err:
            return self.send_db_error(err)

    def assign_task(self, task):
        """ 分配任务和数据锁（如果有）给当前用户。
            1. 如果数据已经被临时锁锁定，则强制抢占——任务数据锁为长时数据锁，比临时数据锁权限高
            2. 如果数据已经被之前发布的任务锁定，这种情况是强制发布新任务，则也强制抢占——这样符合强制发布任务的意图
        """
        # 分配任务
        update = {
            'picked_user_id': self.current_user['_id'],
            'picked_by': self.current_user['name'],
            'status': self.STATUS_PICKED,
            'picked_time': datetime.now(),
            'updated_time': datetime.now(),
        }
        self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        # 分配数据锁
        shared_field = self.get_shared_field(task['task_type'])
        if shared_field:
            collection, id_name = self.get_task_meta(task['task_type'])[:2]
            update = {
                'lock.%s.is_temp' % shared_field: False,
                'lock.%s.lock_type' % shared_field: dict(tasks=task['task_type']),
                'lock.%s.locked_by' % shared_field: self.current_user['name'],
                'lock.%s.locked_user_id' % shared_field: self.current_user['_id'],
                'lock.%s.locked_time' % shared_field: datetime.now()
            }
            self.db[collection].update_one({id_name: task['doc_id']}, {'$set': update})

        self.add_op_log('pick_' + task['task_type'], context=task['doc_id'])
        return self.send_data_response({'url': '/task/do/%s/%s' % (task['task_type'], task['_id']),
                                        'doc_id': task['doc_id'], 'task_id': task['_id']})


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_type/@task_id'

    def post(self, task_type, task_id):
        """ 用户退回任务 """
        try:
            task = self.db.task.find_one({'_id': ObjectId(task_id), 'picked_user_id': self.current_user['_id']})
            if not task:
                return self.send_error_response(errors.no_object)
            # 退回任务
            update = {'status': self.STATUS_RETURNED, 'updated_time': datetime.now(),
                      'returned_reason': self.get_request_data().get('reason')}
            r = self.db.task.update_one({'_id': task['_id']}, {'$set': update})
            if r.matched_count:
                self.add_op_log('return_' + task_type, context=task_id)

            # 释放数据锁（领取任务时分配的长时数据锁）
            shared_field = self.get_shared_field(task_type)
            self.release_temp_lock(task['doc_id'], shared_field)

            return self.send_data_response()

        except DbError as err:
            return self.send_db_error(err)


class RetrieveTaskApi(TaskHandler):
    URL = '/api/task/retrieve/@task_type'

    def post(self, task_type):
        """ 管理员撤回进行中的任务 """
        assert task_type in self.task_types
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'task_ids')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)

            # 撤回进行中的任务
            ret = {'count': 0}
            task_ids = [ObjectId(t) for t in data['task_ids']]
            update = {'status': self.STATUS_RETRIEVED, 'updated_time': datetime.now()}
            r = self.db.task.update_many({'_id': {'$in': task_ids}, 'status': self.STATUS_PICKED}, {'$set': update})
            if r.matched_count:
                ret['count'] = r.matched_count
                self.add_op_log('retrieve_' + task_type, context=data['task_ids'])

            # 释放数据锁（领取任务时分配的长时数据锁）
            tasks = self.db.task.find({'_id': {'$in': task_ids}})
            shared_field = self.get_shared_field(task_type)
            self.release_task_lock([t['doc_id'] for t in tasks], shared_field)

            return self.send_data_response(ret)

        except DbError as err:
            return self.send_db_error(err)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete/@task_type'

    def post(self, task_type):
        """ 删除已发布或悬挂的任务 """
        assert task_type in self.task_types
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'task_ids')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)

            # 删除已发布或悬挂的任务
            ret = {'count': 0}
            task_ids = [ObjectId(t) for t in data['task_ids']]
            condition = {'_id': {'$in': task_ids}, 'status': {'$in': [self.STATUS_OPENED, self.STATUS_PENDING]}}
            r = self.db.task.delete_many(condition)
            if r.deleted_count:
                ret['count'] = r.deleted_count
                self.add_op_log('delete_' + task_type, context=data['task_ids'])

            # 释放数据锁（领取任务时分配的长时数据锁）
            tasks = self.db.task.find({'_id': {'$in': task_ids}})
            shared_field = self.get_shared_field(task_type)
            self.release_task_lock([t['doc_id'] for t in tasks], shared_field)

            return self.send_data_response(ret)

        except DbError as err:
            return self.send_db_error(err)


class AssignTasksApi(TaskHandler):
    URL = '/api/task/assign/@task_type'

    @staticmethod
    def can_user_access(task_type, user):
        user_roles = ','.join(get_all_roles(user.get('roles')))
        return can_access(user_roles, '/api/task/pick/%s' % task_type, 'POST')

    def post(self, task_type):
        """ 指派已发布的任务 """

        assert task_type in self.task_types
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'task_ids', 'user_id')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            user = self.db.user.find_one({'_id': ObjectId(data['user_id'])})
            if not user:
                return self.send_error_response(e.no_user)

            # 检查用户权限（管理员指派任务时，仅检查用户角色）
            if not self.can_user_access(task_type, user):
                return self.send_error_response(e.task_unauthorized)

            # 批量分配已发布的任务
            ret = {'count': 0}
            opened_tasks = self.db.task.find({
                '_id': {'$in': [ObjectId(t) for t in data['task_ids']]},
                'status': self.STATUS_OPENED
            })
            update = {
                'picked_user_id': user['_id'],
                'picked_by': user['name'],
                'status': self.STATUS_PICKED,
                'picked_time': datetime.now(),
                'updated_time': datetime.now(),
            }
            opened_task_ids = [t['_id'] for t in opened_tasks]
            r = self.db.task.update_many({'_id': {'$in': opened_task_ids}}, {'$set': update})
            if r.modified_count:
                ret['count'] = r.modified_count
                self.add_op_log('assign_' + task_type, context=opened_task_ids)

            # 批量分配数据锁
            shared_field = self.get_shared_field(task_type)
            if shared_field:
                update = {
                    'lock.%s.is_temp' % shared_field: False,
                    'lock.%s.lock_type' % shared_field: dict(tasks=task_type),
                    'lock.%s.locked_by' % shared_field: user['name'],
                    'lock.%s.locked_user_id' % shared_field: user['_id'],
                    'lock.%s.locked_time' % shared_field: datetime.now()
                }
                collection, id_name = self.get_task_meta(task_type)[:2]
                doc_ids = [t['doc_id'] for t in opened_tasks]
                self.db[collection].update_many({id_name: {'$in': doc_ids}}, {'$set': update})

            return self.send_data_response(ret)

        except DbError as err:
            return self.send_db_error(err)


class FinishTaskApi(TaskHandler):
    URL = ['/api/task/finish/@task_type/@task_id']

    def post(self, task_type, task_id):
        """ 提交任务，释放数据锁，并且更新后置任务状态。"""
        try:
            task = self.db.task.find_one({'task_type': task_type, '_id': ObjectId(task_id)})
            if not task:
                return self.send_error_response(errors.no_object)
            ret = self.finish_task(task)
            return self.send_data_response(ret)
        except DbError as err:
            return self.send_db_error(err)


class LockTaskDataApi(TaskHandler):
    URL = '/api/data/lock/@shared_field/@doc_id'

    def post(self, shared_field, doc_id):
        """ 获取临时数据锁。"""
        assert shared_field in self.data_auth_maps
        try:
            r = self.get_data_lock(doc_id, shared_field)
            if r is True:
                return self.send_data_response()
            else:
                return self.send_error_response(r)

        except DbError as err:
            return self.send_db_error(err)


class UnlockTaskDataApi(TaskHandler):
    URL = '/api/data/unlock/@shared_field/@doc_id'

    def post(self, shared_field, doc_id):
        """ 释放临时数据锁。"""
        assert shared_field in self.data_auth_maps
        try:
            self.release_temp_lock(doc_id, shared_field)
            return self.send_data_response()

        except DbError as err:
            return self.send_db_error(err)
