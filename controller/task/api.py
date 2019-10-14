#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
from controller import errors
from datetime import datetime
import controller.validate as v
from controller.base import DbError
from bson import objectid
from controller.task.base import TaskHandler
from .view import TaskLobbyHandler as Lobby


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type, doc_id=None):
        """ 领取任务。
        :param task_type: 任务类型。如果是组任务，用户只能领取一份数据的一组任务中的一个。
        :param doc_id: 任务名称。如果为空，则任取一个。
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
                message = '您还有未完成的任务(%s)，请完成后再领取新任务' % uncompleted['doc_id']
                url = '/task/do/%s/%s' % (task_type, uncompleted['doc_id'])
                return self.send_error_response(
                    (errors.task_uncompleted[0], message),
                    **{'uncompleted_id': uncompleted['doc_id'], 'url': url}
                )

            # 如果doc_id为空，则任取一个任务
            doc_id = self.get_request_data().get('doc_id')
            if not doc_id:
                task = Lobby.get_lobby_tasks_by_type(self, task_type, page_size=1)
                return self.assign_task(task)

            # 检查任务是否存在
            collection, id_name = self.task_meta(task_type)[:2]
            tasks = list(self.db.task.find({
                'task_type': {'$regex': '.*%s.*' % task_type} if task_meta.get('groups') else task_type,
                'collection': collection, 'id_name': id_name, 'doc_id': doc_id
            }))
            if not tasks:
                return self.send_error_response(errors.no_object)

            # 检查任务状态是否为已发布
            opened_tasks = [t for t in tasks if t['status'] == self.STATUS_OPENED]
            if not opened_tasks:
                return self.send_error_response(errors.task_not_published)

            # 如果任务有共享数据，则检查对应的数据是否被锁定
            shared_field = task_meta['data'].get('shared_field')
            if shared_field and shared_field in self.data_auth_maps:
                if self.is_data_locked(collection, id_name, doc_id, shared_field):
                    return self.send_error_response(errors.data_is_locked)

            # 如果任务为组任务，则检查用户是否曾领取该组任务中的任务
            picked_tasks = [t for t in tasks if t.get('picked_user_id') == self.current_user['_id']]
            if task_meta.get('groups') and picked_tasks:
                return self.send_error_response(errors.task_text_proof_duplicated)

            # 将任务和数据锁分配给用户
            return self.assign_task(opened_tasks[0])

        except DbError as e:
            self.send_db_error(e)

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
        return self.send_data_response({'url': '/task/do/%s/%s' % (task['task_type'], task['doc_id']),
                                        'doc_id': task['doc_id']})


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

    def finish_task(self, task_type, doc_id):
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
