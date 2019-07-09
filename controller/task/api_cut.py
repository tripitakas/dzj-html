#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
import re
from datetime import datetime
import controller.errors as errors
from controller.base import DbError
from tornado.escape import json_decode
from controller.task.api_base import SubmitTaskApi


class SaveCutApi(SubmitTaskApi):
    URL = ['/api/task/do/@box_type_cut_proof/@page_name',
           '/api/task/update/@box_type_cut_proof/@page_name',
           '/api/task/do/@box_type_cut_review/@page_name',
           '/api/task/update/@box_type_cut_review/@page_name',
           '/api/data/edit/@box_types/@page_name']

    save_fields = {
        'block_cut_proof': 'blocks', 'block_cut_review': 'blocks', 'column_cut_proof': 'columns',
        'column_cut_review': 'columns', 'char_cut_proof': 'chars', 'char_cut_review': 'chars',
    }

    def post(self, kind, page_name):
        """ 保存数据。有do/update/edit三种模式:
            1. do。做任务时，保存或提交任务。
            2. update。任务完成后，本任务用户修改数据。
            3. edit。任何时候，有数据锁的用户修改数据。
            根据情况，do和update需要检查任务归属和数据锁，edit需要检查数据锁。
        """
        try:
            # 保存任务
            task_type = '%s_cut_%s' % (kind, 'review' if 'review' in self.request.path else 'proof')
            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['do'])[0]
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            ret = {'updated': True}
            data = self.get_request_data()
            boxes = json_decode(data.get('boxes', '[]'))
            data_field = self.save_fields.get(task_type)
            update = {data_field: boxes, 'tasks.%s.updated_time' % task_type: datetime.now()}
            if 'do/char_cut' in self.request.path and data.get('commit'):  # 切字commit
                update.update({'tasks.%s.committed' % task_type: [task_type]})

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            # 提交任务
            if mode == 'do' and data.get('submit'):
                ret.update(self.submit(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)
