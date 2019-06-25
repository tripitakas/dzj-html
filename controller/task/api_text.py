#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
import controller.errors as errors
from controller.base import DbError
from tornado.escape import json_decode
from controller.task.base import TaskHandler


class SaveTextApi(TaskHandler):
    """ 保存数据。有do/update两种模式。1. do。做任务时，保存或提交任务。2. update。任务完成后，本任务用户修改数据。
        不提供其他人修改，因此仅检查任务归属，无需检查数据锁。
    """

    save_fields = {
        'text_proof_1': 'txt1',
        'text_proof_2': 'txt2',
        'text_proof_3': 'txt3',
        'text_review': 'text'
    }

    def save(self, task_type, page_name, mode):
        try:
            assert task_type in self.text_task_names() and mode in ['do', 'update', 'edit']

            data = self.get_request_data()
            txt = data.get('txt') and re.sub(r'\|+$', '', json_decode(data['txt']).replace('\n', '|'))
            doubt = self.get_request_data().get('doubt')

            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            data_field = self.save_fields.get(task_type)
            update = {
                data_field: txt,
                'tasks.%s.doubt' % task_type: doubt,
                'tasks.%s.updated_time' % task_type: datetime.now()
            }

            if mode == 'do' and data.get('submit'):
                update.update({
                    'tasks.%s.status' % task_type: self.STATUS_FINISHED,
                    'tasks.%s.finished_time' % task_type: datetime.now(),
                })

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            if mode == 'do' and data.get('submit'):
                # 处理后置任务
                self.update_post_tasks(page_name, task_type)

            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class SaveTextProofApi(SaveTextApi):
    URL = ['/api/task/do/text_proof_@num/@page_name',
           '/api/task/update/text_proof_@num/@page_name']

    def post(self, num, page_name):
        """ 保存或提交文字校对任务 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update'
        self.save('text_proof_' + num, page_name, mode=mode)


class SaveTextReviewApi(SaveTextApi):
    URL = ['/api/task/do/text_review/@page_name',
           '/api/task/update/text_review/@page_name']

    def post(self, num, page_name):
        """ 保存或提交文字审定任务 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update'
        self.save('text_review', page_name, mode=mode)
