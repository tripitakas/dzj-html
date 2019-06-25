#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
from datetime import datetime
from controller.base import DbError
from tornado.escape import json_decode
from controller.task.base import TaskHandler
import controller.errors as errors


class SaveCutApi(TaskHandler):
    """ 保存数据。有do/update/edit三种模式。1. do。做任务时，保存或提交任务。2. update。任务完成后，本任务用户修改数据。
        3. edit。任何时候，有数据锁的用户修改数据。
        根据情况，do和update需要检查任务归属和数据锁，edit需要检查数据锁。
    """

    save_fields = {
        'block_cut_proof': 'blocks',
        'block_cut_review': 'blocks',
        'column_cut_proof': 'columns',
        'column_cut_review': 'columns',
        'char_cut_proof': 'chars',
        'char_cut_review': 'chars',
    }

    def save(self, task_type, page_name, mode):
        try:
            assert task_type in self.cut_task_names() and mode in ['do', 'update', 'edit']

            data = self.get_request_data()
            boxes = json_decode(data.get('boxes', '[]'))

            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            data_field = self.save_fields.get(task_type)
            update = {
                data_field: boxes,
                'tasks.%s.updated_time' % task_type: datetime.now()
            }
            if mode == 'do' and data.get('submit'):
                update.update({
                    'tasks.%s.status' % task_type: self.STATUS_FINISHED,
                    'tasks.%s.finished_time' % task_type: datetime.now(),
                    'lock.%s' % data_field: {},
                })

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            if mode == 'do' and data.get('submit'):
                self.update_post_tasks(page_name, task_type)  # 处理后置任务

            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class SaveCutProofApi(SaveCutApi):
    URL = ['/api/task/do/@box_type_cut_proof/@page_name',
           '/api/task/update/@box_type_cut_proof/@page_name',
           '/api/data/edit/@box_types/@page_name']

    def post(self, kind, page_name):
        """ 保存或提交切分校对任务 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update' if '/update' in p else 'edit'
        self.save(kind + '_cut_proof', page_name, mode=mode)


class SaveCutReviewApi(SaveCutApi):
    URL = ['/api/task/do/@box_type_cut_review/@page_name',
           '/api/task/update/@box_type_cut_review/@page_name']

    def post(self, kind, page_name):
        """ 保存或提交切分审定任务 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update'
        self.save(kind + '_cut_review', page_name, mode=mode)
