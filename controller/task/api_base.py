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
            uncompleteds = self.get_my_tasks_by_type(task_type, status=self.STATUS_PICKED)[0]
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

            # 检查任务对应的数据是否被锁定。如果没有申明要保护，则直接跳过。
            data_field = self.get_shared_data_field(task_type)
            if (data_field and data_field in self.data_auth_maps
                    and self.prop(task, 'lock.%s.locked_user_id' % data_field)):
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
        """ 将任务和数据锁（如果有的话）分配给当前用户 """
        task_field = 'tasks.' + task_type
        update = {
            task_field + '.picked_user_id': self.current_user['_id'],
            task_field + '.picked_by': self.current_user['name'],
            task_field + '.status': self.STATUS_PICKED,
            task_field + '.picked_time': datetime.now(),
            task_field + '.updated_time': datetime.now(),
        }
        data_field = self.get_shared_data_field(task_type)
        if data_field:
            update['lock.' + data_field] = {
                "is_temp": False,
                "lock_type": dict(tasks=task_type),
                "locked_by": self.current_user['name'],
                "locked_user_id": self.current_user['_id'],
                "locked_time": datetime.now()
            }
        r = self.db.page.update_one({'name': page_name}, {'$set': update})
        if r.matched_count:
            self.add_op_log('pick_' + task_type, context=page_name)
            return self.send_data_response({'page_name': page_name, 'url': '/task/do/%s/%s' % (task_type, page_name)})
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

            data_field, ret = 'tasks.' + task_type, {'returned': True}
            update = {
                data_field + '.status': self.STATUS_RETURNED,
                data_field + '.updated_time': datetime.now(),
                data_field + '.returned_reason': self.get_request_data().get('reason'),
            }
            # 检查数据锁
            data_field = self.get_shared_data_field(task_type)
            if data_field and data_field in self.data_auth_maps:
                update.update({'lock.' + data_field: dict()})
                ret['data_lock_released'] = True
            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.matched_count:
                self.add_op_log('return_' + task_type, context=page_name)

            return self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SubmitTaskApi(TaskHandler):

    def submit(self, task_type, page_name):
        """ 任务提交 """
        # 更新当前任务
        ret = {'submitted': True}
        update = {
            'tasks.%s.status' % task_type: self.STATUS_FINISHED,
            'tasks.%s.finished_time' % task_type: datetime.now(),
        }

        # 释放数据锁
        data_field = self.get_shared_data_field(task_type)
        if data_field in self.data_auth_maps:
            update['lock.' + data_field] = {}
            ret['data_lock_released'] = True

        r = self.db.page.update_one({'name': page_name}, {'$set': update})
        if r.modified_count:
            self.add_op_log('submit_' + task_type, context=page_name)

        # 更新后置任务
        self.update_post_tasks(page_name, task_type)
        ret['post_tasks_updated'] = True

        return ret


class UnlockTaskDataApi(TaskHandler):
    URL = '/api/task/unlock/@task_type/@page_name'

    def post(self, task_type, page_name):
        """ 释放数据锁。仅能释放由update和edit而申请的临时数据锁，不能释放do做任务的长时数据锁。"""
        try:
            data_field = self.get_shared_data_field(task_type)
            self.release_temp_data_lock(page_name, data_field)
            self.send_data_response()
        except DbError as e:
            self.send_db_error(e)


class WithDrawTaskApi(TaskHandler):
    URL = '/api/task/withdraw/@task_type/@page_name'

    def post(self, task_type, page_name):
        """ 管理员撤回任务 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.send_error_response(errors.no_object)
            status = self.prop(page, 'tasks.%s.status' % task_type)
            if status not in [self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED]:
                return self.send_error_response(errors.task_not_allowed_withdraw)

            update = {'tasks.%s' % task_type: dict(status=self.STATUS_READY)}
            data_field = self.get_shared_data_field(task_type)
            if data_field:  # 释放数据锁
                update.update({'lock.'+data_field: dict()})
            r = self.db.page.update_one(dict(name=page_name), {'$set': update})
            if not r.matched_count:
                return self.send_error_response(errors.no_object)
            self.add_op_log('withdraw_'+task_type, target_id=page['_id'], context=page_name)
            self.send_data_response({'page_name': page_name})

        except DbError as e:
            self.send_db_error(e)


class ResetTaskApi(TaskHandler):
    URL = '/api/task/reset/@task_type/@page_name'

    def post(self, task_type, page_name):
        """ 管理员重置任务为未就绪 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.send_error_response(errors.no_object)
            status = self.prop(page, 'tasks.%s.status' % task_type)
            if status != self.STATUS_READY:
                return self.send_error_response(errors.task_not_allowed_reset)

            update = {'tasks.%s' % task_type: dict(status=self.STATUS_UNREADY)}
            r = self.db.page.update_one(dict(name=page_name), {'$set': update})
            if not r.matched_count:
                return self.send_error_response(errors.no_object)
            self.add_op_log('reset_' + task_type, target_id=page['_id'], context=page_name)
            self.send_data_response({'page_name': page_name})

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
