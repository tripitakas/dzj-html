#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
import re
from datetime import datetime
import controller.validate as v
import controller.errors as errors
from controller.base import DbError
from tornado.escape import json_decode
from controller.task.view_cut import CutHandler
from controller.task.api_base import SubmitTaskApi


class SaveCutApi(SubmitTaskApi):
    URL = ['/api/task/do/@cut_type/@page_name',
           '/api/task/update/@cut_type/@page_name']

    def post(self, task_type, page_name):
        """ 保存数据。有do/update/edit三种模式:
            1. do。做任务时，保存或提交任务。
            2. update。任务完成后，本任务用户修改数据。
            根据情况，do和update需要检查任务归属和数据锁。
        """
        try:
            # 检查参数
            data = self.get_request_data()
            rules = [(v.not_empty, 'step', 'boxes')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(errors.no_object)
            steps_todo = self.prop(page, 'tasks.%s.steps.todo' % task_type) or CutHandler.default_steps.keys()
            if not data['step'] in steps_todo:
                self.send_error_response(errors.task_step_error)

            # 检查权限
            mode = (re.findall('(do|update)/', self.request.path) or ['do'])[0]
            if not self.check_auth(mode, page, task_type):
                self.send_error_response(errors.data_unauthorized)

            # 保存数据
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}
            data_field = data['step'].strip('_box') + 's'
            update.update({data_field: json_decode(data['boxes'])})
            if data.get('submit'):
                submitted = self.prop(page, 'tasks.%s.steps.submitted' % task_type) or []
                if data['step'] not in submitted:
                    submitted.append(data['step'])
                update.update({'tasks.%s.steps.submitted' % task_type: submitted})
            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_%s_%s' % (mode, task_type), context=page_name)

            # 提交任务
            ret = {'updated': True}
            if mode == 'do' and data.get('submit') and data['step'] == steps_todo[-1]:
                ret.update(self.submit(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveCutEditApi(SubmitTaskApi):
    URL = '/api/data/cut_edit/@page_name'

    def post(self, page_name):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
        try:
            # 检查参数
            data = self.get_request_data()
            rules = [(v.not_empty, 'step', 'boxes')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(errors.no_object)
            steps_todo = CutHandler.default_steps.keys()
            if not data['step'] in steps_todo:
                self.send_error_response(errors.task_step_error)

            # 检查权限
            if not self.check_auth('edit', page, 'cut_edit'):
                self.send_error_response(errors.data_unauthorized)

            # 保存数据
            data_field = data['step'].strip('_box') + 's'
            r = self.db.page.update_one({'name': page_name}, {'$set': {data_field: json_decode(data['boxes'])}})
            if r.modified_count:
                self.add_op_log('save_edit_%s' % data_field, context=page_name)
            self.send_data_response({'updated': True})

        except DbError as e:
            self.send_db_error(e)