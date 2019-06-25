#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
from controller import errors
from datetime import datetime
from controller.base import DbError
from controller.task.base import TaskHandler


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type'

    def post(self, task_type):
        """ 领取任务 """
        self.pick(self, task_type, self.get_request_data().get('page_name'))

    @staticmethod
    def pick(self, task_type, page_name=None):
        """ 领取任务。
        :param task_type: 任务类型。可以是block_cut_proof/text_proof_1等，也可以为text_proof
        :param page_name: 任务名称。如果为空，则任取一个。
        """
        try:
            # 检查是否有未完成的任务
            uncompleteds = self.get_my_tasks_by_type(task_type, status=[self.STATUS_PICKED])[0]
            if uncompleteds:
                message = '您还有未完成的任务(%s)，请完成后再领取新任务' % uncompleteds[0]['name']
                url = '/task/do/%s/%s' % (task_type, uncompleteds[0]['name'])
                return self.send_error_response(
                    (errors.task_uncompleted[0], message),
                    **{'uncompleted_name': uncompleteds[0]['name'], 'url': url}
                )

            # 如果page_name为空，则任取一个任务
            if not page_name:
                return self.pick_one_from_lobby(self, task_type)

            # 检查页面是否存在
            task = self.db.page.find_one({'name': page_name}, self.simple_fileds())
            if not task:
                return self.send_error_response(errors.no_object)

            # 检查页面状态是否为已发布（不可为其它状态，如未就绪、未发布、已领取等等）
            if self.prop(task, 'tasks.%s.status' % task_type) != self.STATUS_OPENED:
                return self.send_error_response(errors.task_not_published)

            # 检查任务对应的数据是否被锁定
            data_type = self.get_data_type(task_type)
            if self.prop(task, 'lock.%s.locked_user_id' % data_type):
                return self.send_error_response(errors.data_is_locked)

            # 文字校对中，不能领取同一page不同校次的两个任务
            if 'text_proof' in task_type:
                for i in range(1, 4):
                    if self.prop(task, 'tasks.text_proof_%s.picked_user_id' % i) == self.current_user['_id']:
                        return self.send_error_response(errors.task_text_proof_duplicated)

            # 将任务和数据锁分配给用户
            return PickTaskApi.assign_task(self, page_name, task_type)

        except DbError as e:
            self.send_db_error(e)

    @staticmethod
    def assign_task(self, page_name, task_type):
        """ 将任务和数据锁分配给当前用户 """
        data_type = self.get_data_type(task_type)
        task_field, lock_field = 'tasks.' + task_type, 'lock.' + data_type
        r = self.db.page.update_one({'name': page_name}, {'$set': {
            lock_field: {
                "lock_type": ('tasks', task_type),
                "locked_by": self.current_user['name'],
                "locked_user_id": self.current_user['_id'],
                "locked_time": datetime.now()
            },
            task_field + '.picked_user_id': self.current_user['_id'],
            task_field + '.picked_by': self.current_user['name'],
            task_field + '.status': self.STATUS_PICKED,
            task_field + '.picked_time': datetime.now(),
            task_field + '.updated_time': datetime.now(),
        }})
        if r.matched_count:
            self.add_op_log('pick_' + task_type, context=page_name)
            return self.send_data_response({'url': '/task/do/%s/%s' % (task_type, page_name)})
        else:
            return self.send_error_response(errors.no_object)

    @staticmethod
    def pick_one_from_lobby(self, task_type):
        """ 从任务大厅中随机领取一个任务"""
        tasks = self.get_lobby_tasks_by_type(task_type, page_size=1)[0]
        if not tasks:
            return self.send_error_response(errors.no_task_to_pick)
        else:
            task_type = self.select_lobby_text_proof(tasks[0]) if task_type == 'text_proof' else task_type
            return self.assign_task(self, tasks[0]['name'], task_type)


class UnlockDataApi(TaskHandler):
    URL = '/api/task/data/unlock/@data_type/@page_name'

    def get(self, data_type, page_name):
        """ 释放数据锁。这里仅仅释放由临时的数据编辑而申请的数据锁，对于领取任务获得的数据锁，在提交任务时释放。"""
        try:
            self.release_data_lock(page_name, data_type)
            self.send_data_response({'page_name': page_name})
        except DbError as e:
            self.send_db_error(e)


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_type/@page_name'

    def post(self, task_type, page_name):
        """ 用户主动退回当前任务 """
        try:
            page = self.db.page.find_one({'name': page_name}, self.simple_fileds())
            if not page:
                return self.send_error_response(errors.no_object)
            elif self.prop(page, 'tasks.%s.picked_user_id' % task_type) != self.current_user['_id']:
                return self.send_error_response(errors.unauthorized)
            elif self.prop(page, 'tasks.%s.status' % task_type) == self.STATUS_FINISHED:
                return self.send_error_response(errors.task_return_only_picked)
            elif self.prop(page, 'tasks.%s.status' % task_type) != self.STATUS_PICKED:
                return self.send_error_response(errors.task_return_only_picked)

            task_field = 'tasks.' + task_type
            r = self.db.page.update_one({'name': page_name}, {'$set': {
                task_field + '.status': self.STATUS_RETURNED,
                task_field + '.updated_time': datetime.now(),
                task_field + '.returned_reason': self.get_request_data().get('reason'),
            }})
            if r.matched_count:
                self.add_op_log('return_' + task_type, file_id=str(page['_id']), context=page_name)

            # 释放数据锁
            self.release_data_lock(page_name, self.get_data_type(task_type))

            return self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class GetPageApi(TaskHandler):
    URL = '/api/task/page/@page_name'

    def get(self, name):
        """ 获取单个页面 """
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error_response(errors.no_object)
            self.send_data_response(page)

        except DbError as e:
            self.send_db_error(e)
