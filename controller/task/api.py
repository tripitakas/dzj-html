#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
from bson import objectid
from datetime import datetime
from controller import errors
import controller.errors as e
import controller.validate as v
from controller.base import DbError
from controller.task.base import TaskHandler
from controller.task.publish import PublishBaseHandler
from .view import TaskLobbyHandler as Lobby


class GetReadyTasksApi(TaskHandler):
    URL = '/api/task/ready/@task_type'

    def post(self, task_type):
        """ 查找任务对应的collection，获取已就绪的数据列表 """
        assert task_type in self.task_types
        try:
            data = self.get_request_data()
            collection, id_name, input_field, shared_field = self.task_meta(task_type)
            doc_id = dict()
            if data.get('prefix'):
                doc_id.update({'$regex': '.*%s.*' % data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                doc_id.update({'$nin': data.get('exclude')})
            condition = {id_name: doc_id} if doc_id else {}
            if input_field:
                condition.update({input_field: {'$nin': [None, '']}})  # 任务所依赖的数据字段存在且不为空
            page_no = int(data.get('page', 0)) if int(data.get('page', 0)) > 1 else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db[collection].count_documents(condition)
            docs = self.db[collection].find(condition).limit(page_size).skip(page_size * (page_no - 1))
            response = {'docs': [d[id_name] for d in list(docs)], 'page_size': page_size,
                        'page_no': page_no, 'total_count': count}
            self.send_data_response(response)
        except DbError as err:
            self.send_db_error(err)


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
                collection, id_name, input_field, shared_field = self.task_meta(data['task_type'])
                condition = {id_name: {'$regex': '.*%s.*' % data['prefix'], '$options': '$i'},
                             input_field: {"$nin": [None, '']}}
                docs = self.db[collection].find(condition)
                doc_ids = [doc.get(id_name) for doc in docs]
        return doc_ids

    def post(self):
        """ 根据数据id发布任务。
        @param task_type 任务类型
        @param steps list，步骤
        @param pre_tasks list，前置任务
        @param ids str，待发布的任务名称
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
            doc_ids = data['doc_ids'].split(',') if isinstance(data['doc_ids'], str) else data['doc_ids']
            if len(doc_ids) > self.MAX_PUBLISH_RECORDS:
                return self.send_error_response(e.task_exceed_max, message='任务数量不能超过%s' % self.MAX_PUBLISH_RECORDS)

            force = data['force'] == '1'
            log = self.publish_task(data['task_type'], data.get('pre_tasks', []), data.get('steps', []),
                                    data['priority'], force, doc_ids=doc_ids)
            self.send_data_response({k: value for k, value in log.items() if value})

        except DbError as err:
            self.send_db_error(err)


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type):
        """ 领取任务。
        :param task_type: 任务类型。如果是组任务，用户只能领取一份数据的一组任务中的一个。
        """
        try:
            # 检查是否有未完成的任务
            task_meta = self.all_task_types()[task_type]
            condition = {
                'task_type': {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type,
                'picked_user_id': self.current_user['_id'],
                'status': self.STATUS_PICKED,
            }
            uncompleted = self.db.task.find_one(condition)
            if uncompleted:
                url = '/task/do/%s/%s' % (task_type, uncompleted['_id'])
                return self.send_error_response(
                    e.task_uncompleted, **{'doc_id': uncompleted['doc_id'], 'url': url}
                )

            # 如果_id为空，则任取一个任务
            _id = self.get_request_data().get('_id')
            if not _id:
                task = Lobby.get_lobby_tasks_by_type(self, task_type, page_size=1)[0][0]
                return self.assign_task(task)

            # 检查任务及任务状态
            task = self.db.task.find_one({'_id': objectid.ObjectId(_id)})
            if not task:
                return self.send_error_response(e.no_object)
            if task['status'] != self.STATUS_OPENED:
                return self.send_error_response(e.task_not_published)

            # 如果任务有共享数据，则检查对应的数据是否被锁定
            shared_field = self.get_shared_field(task_type)
            c, i, d = task['collection'], task['id_name'], task['doc_id']
            if shared_field and shared_field in self.data_auth_maps:
                if self.is_data_locked(c, i, d, shared_field):
                    return self.send_error_response(e.data_is_locked)

            # 如果任务为组任务，则检查用户是否曾领取过该组任务
            condition = dict(task_type=task_type, collection=c, id_name=i, doc_id=d,
                             picked_user_id=self.current_user['_id'])
            if task_meta.get('groups') and self.db.task.find_one(condition):
                return self.send_error_response(e.group_task_duplicated)

            # 分配任务及数据锁
            return self.assign_task(task)

        except DbError as err:
            self.send_db_error(err)

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
            collection, id_name = self.task_meta(task['task_type'])[:2]
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
                                        'doc_id': task['doc_id'], '_id': task['_id']})


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_type/@doc_id'

    def post(self, task_type, doc_id):
        """ 用户退回任务 """
        try:
            tasks = self.find_tasks(task_type, doc_id, self.STATUS_PICKED, mine=True)
            if not tasks:
                return self.send_error_response(errors.no_object)
            # 退回任务
            ret = {'returned': True}
            update = {'status': self.STATUS_RETURNED, 'updated_time': datetime.now(),
                      'returned_reason': self.get_request_data().get('reason')}
            r = self.db.task.update_one({'_id': tasks[0]['_id']}, {'$set': update})
            if r.matched_count:
                self.add_op_log('return_' + task_type, context=doc_id)

            # 释放数据锁（领取任务时分配的长时数据锁）
            collection, id_name, input_field, shared_field = self.task_meta(task_type)
            if shared_field and shared_field in self.data_auth_maps:
                self.release_data_lock(collection, id_name, doc_id, shared_field, is_temp=False)
                ret['data_lock_released'] = True

            return self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class RetrieveTaskApi(TaskHandler):
    URL = '/api/task/retrieve/@task_type/@doc_id'

    def post(self, task_type, doc_id):
        """ 管理员强制撤回进行中的任务 """
        try:
            tasks = self.find_tasks(task_type, doc_id, self.STATUS_PICKED)
            if not tasks:
                return self.send_error_response(errors.no_object)
            # 强制撤回任务
            ret = {'retrieved': True}
            update = {'status': self.STATUS_RETRIEVED, 'updated_time': datetime.now()}
            r = self.db.task.update_one({'_id': tasks[0]['_id']}, {'$set': update})
            if r.matched_count:
                self.add_op_log('retrieve_' + task_type, context=doc_id)

            # 释放数据锁（领取任务时分配的长时数据锁）
            collection, id_name, input_field, shared_field = self.task_meta(task_type)
            if shared_field and shared_field in self.data_auth_maps:
                self.release_data_lock(collection, id_name, doc_id, shared_field, is_temp=False)
                ret['data_lock_released'] = True

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class DeleteTasksApi(TaskHandler):
    URL = '/api/task/delete'

    def post(self):
        """ 批量删除任务 """
        data = self.get_request_data()
        rules = [(v.not_empty, 'ids')]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        try:
            ids = data['ids'].strip(',').split(',') if data.get('ids') else []
            condition = {'status': {'$in': [self.STATUS_OPENED, self.STATUS_PENDING]},
                         '_id': {'$in': [objectid.ObjectId(i) for i in ids]}}
            r = self.db.task.delete_many(condition)
            self.add_op_log('delete_tasks', context=ids)
            self.send_data_response({'deleted_count': r.deleted_count})

        except DbError as e:
            self.send_db_error(e)


# to delete
class FinishTaskApi(TaskHandler):

    def finish_task_to_delete(self, task_type, doc_id):
        """ 完成任务提交 """
        # 更新当前任务
        ret = {'submitted': True}
        collection, id_name = self.task_meta(task_type)[:2]
        update = {'status': self.STATUS_FINISHED, 'finished_time': datetime.now()}
        condition = dict(task_type=task_type, collection=collection, id_name=id_name, doc_id=doc_id,
                         picked_user_id=self.current_user['_id'], status=self.STATUS_PICKED)
        r = self.db.task.update_one(condition, {'$set': update})
        if r.modified_count:
            self.add_op_log('finish_' + task_type, context=doc_id)

        # 释放数据锁
        shared_field = self.get_shared_field(task_type)
        if shared_field and shared_field in self.data_auth_maps:
            update['lock.' + shared_field] = {}

            self.db[collection].update_one({id_name: doc_id}, {'$set': update})
            ret['data_lock_released'] = True

        # 更新后置任务
        self.update_post_tasks(doc_id, task_type)
        ret['post_tasks_updated'] = True

        return ret


class UnlockTaskDataApi(TaskHandler):
    URL = ['/api/task/unlock/@task_type/@doc_id',
           '/api/data/unlock/@edit_type/@doc_id']

    def post(self, task_type, doc_id):
        """ 释放数据锁。仅能释放由update和edit而申请的临时数据锁，不能释放do做任务的长时数据锁。"""
        try:
            data_field = self.get_shared_field(task_type)
            self.release_data_lock(doc_id, data_field)
            self.send_data_response()
        except DbError as e:
            self.send_db_error(e)


class GetPageApi(TaskHandler):
    URL = '/api/task/page/@doc_id'

    def get(self, name):
        """ 获取单个页面 """
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error_response(errors.no_object)
            self.send_data_response(page)

        except DbError as e:
            self.send_db_error(e)
