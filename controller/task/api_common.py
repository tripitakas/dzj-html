#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
from controller import errors
from datetime import datetime
from controller.base import DbError
from controller.task.base import TaskHandler
from controller.task.view_lobby import TaskLobbyHandler as Lobby


class PickTaskApi(TaskHandler):
    URL = '/api/task/pick/@task_type/@page_name'

    def get(self, task_type, page_name):
        """ 领取任务 """
        self.pick(self, task_type, page_name)

    @staticmethod
    def pick(self, task_type, page_name=None):
        """ 领取任务。
        :param task_type: 任务类型。比如block_cut_proof/text_proof_1等
        :param page_name: 任务名称。如果为空，则任取一个。
        """
        try:
            # page_name为空，任取一个任务
            if not page_name:
                task = Lobby.get_lobby_tasks_by_type(self, task_type, page_size=1)
                if not task:
                    return self.send_error_response(errors.task_none_to_pick)
                else:
                    self.add_op_log('pick_' + task_type, context=task['name'])
                    return self.send_data_response({'page_name': task['name']})

            # 检查是否有未完成的任务
            task_uncompleted = self.db.page.find_one({
                'tasks.%s.picked_user_id' % task_type: self.current_user['_id'],
                'tasks.%s.status' % task_type: self.STATUS_PICKED
            })
            if task_uncompleted and task_uncompleted['name'] != page_name:
                message = '您还有未完成的任务(%s)，请完成后再领取新任务' % task_uncompleted['name']
                return self.send_error_response(
                    (errors.task_uncompleted[0], message), **{'page_name': task_uncompleted['name']}
                )

            # 检查页面是否存在
            task = self.db.page.find_one({'name': page_name}, self.simple_fileds())
            if not task:
                return self.send_error_response(errors.task_not_existed)

            # 检查页面状态是否为已发布（如未就绪、未发布、已领取等等）
            if self.prop(task, 'tasks.%s.status' % task_type) != self.STATUS_OPENED:
                return self.send_error_response(errors.task_cannot_pick)

            # 检查任务对应的数据是否被锁定
            data_type = self.get_data_type(task_type)
            if self.prop(task, 'lock.%s.locked_user_id' % data_type):
                return self.send_error_response(errors.data_is_locked)

            # 文字校对中，不能领取同一page不同校次的两个任务
            if 'text_proof_' in task_type:
                for i in range(1, 4):
                    if self.prop(task, 'tasks.text_proof_%s.picked_user_id' % i) == self.current_user['_id']:
                        return self.send_error_response(errors.task_text_proof_duplicated)

            # 将任务和数据锁分配给用户
            r = self.db.user.update_one({'name': page_name}, {'$set': {
                'lock.%s' % data_type: {
                    "lock_type": ('tasks', task_type),
                    "locked_by": self.current_user['name'],
                    "locked_user_id": self.current_user['_id'],
                    "locked_time": datetime.now()
                },
                'tasks.%s' % task_type: {
                    'picked_user_id': self.current_user['_id'],
                    'picked_by': self.current_user['name'],
                    'picked_time': datetime.now(),
                    'updated_time': datetime.now(),
                }
            }})
            if r.matched_count:
                self.add_op_log('pick_' + task_type, context=page_name)
                return self.send_data_response({'page_name': page_name})

        except DbError as e:
            self.send_db_error(e)


class UnlockDataApi(TaskHandler):
    URL = '/api/task/data/unlock/@data_type/@page_name'

    def get(self, data_type, page_name):
        """ 释放数据锁
        :param data_type: 数据类型。如果为task_type，则通过计算得到data_type
        """
        try:
            self.release_data_lock(page_name, data_type)
            self.send_data_response()
        except DbError as e:
            self.send_db_error(e)


class ReturnTaskApi(TaskHandler):
    URL = '/api/task/return/@task_type/@page_prefix'

    def post(self, task_type, page_name):
        """ 用户主动退回当前任务 """
        page = self.db.page.find_one({'name': page_name})
        if not page:
            return self.send_error_response(errors.no_object)
        elif self.prop(page, 'tasks.%s.picked_user_id' % task_type) != self.current_user['_id']:
            return self.send_error_response(errors.unauthorized)
        elif self.prop(page, 'tasks.%s.status' % task_type) != self.STATUS_PICKED:
            return self.send_error_response(errors.task_return_only_picked)

        r = self.db.user.update_one({'name': page_name}, {'$set': {
            'tasks.%s' % task_type: {
                'status': self.STATUS_RETURNED,
                'updated_time': datetime.now(),
                'returned_reason': self.get_request_data().get('reason'),
            }
        }})
        if r.matched_count:
            self.add_op_log('return_' + task_type, file_id=str(page['_id']), context=page_name)

        # 释放数据锁
        self.release_data_lock(page_name, task_type)

        return self.send_data_response()


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
