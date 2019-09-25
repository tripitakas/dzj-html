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
from controller.task.view_cut import CutHandler
from controller.task.api_base import SubmitTaskApi


class SaveCutApi(SubmitTaskApi):
    URL = ['/api/task/do/@cut_type/@page_name',
           '/api/task/update/@cut_type/@page_name',
           '/api/data/(cut_edit)/@page_name']

    def post(self, task_type, page_name):
        """ 保存数据。有do/update/edit三种模式:
            1. do。做任务时，保存或提交任务。
            2. update。任务完成后，本任务用户修改数据。
            3. edit。任何时候，有数据锁的用户修改数据。
            根据情况，do和update需要检查任务归属和数据锁，edit需要检查数据锁。
        """
        try:
            # 保存任务
            mode = (re.findall('(do|update|edit)/', self.request.path) or ['do'])[0]
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            ret = {'updated': True}
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}

            data = self.get_request_data()
            boxes = json_decode(data.get('boxes', '[]'))
            step = int(data.get('step', '1'))
            is_last_step = step == len(CutHandler.step_names)
            if boxes:
                box_name = CutHandler.step_boxes[step - 1]
                update.update({'cut.%s' % box_name: boxes})
                if not is_last_step and data.get('submit'):
                    update.update({'tasks.%s.current_step' % task_type: step + 1})

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_%s_%s' % (mode, task_type), context=page_name)

            # 提交任务
            if is_last_step and mode == 'do' and data.get('submit'):
                ret.update(self.submit(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)