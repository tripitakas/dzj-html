#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
import re
from .view import CutHandler
from datetime import datetime
import controller.validate as v
import controller.errors as errors
from bson.objectid import ObjectId
from controller.base import DbError
from tornado.escape import json_decode
from controller.task.api import FinishTaskApi


class SaveCutApi(FinishTaskApi):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    def post(self, task_type, task_id):
        """ 保存数据。
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
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(errors.no_object)
            steps_todo = self.prop(task, 'steps.todo')
            if not data['step'] in steps_todo:
                self.send_error_response(errors.task_step_error)

            # 检查权限
            mode = (re.findall('(do|update)/', self.request.path) or ['do'])[0]
            if not self.check_auth(task, mode):
                self.send_error_response(errors.data_unauthorized)

            # 保存数据
            ret = {'updated': True}
            update = {'updated_time': datetime.now()}
            data_field = re.sub('(_box|_order)', 's', data['step'])
            update.update({data_field: json_decode(data['boxes'])})
            collection, id_name = self.task_meta(task_type)[:2]
            self.db[collection].update_one({id_name: task['doc_id']}, {'$set': update})

            # 提交步骤
            if data.get('submit'):
                update = {'updated_time': datetime.now()}
                submitted = self.prop(task, 'steps.submitted') or []
                if data['step'] not in submitted:
                    submitted.append(data['step'])
                update.update({'steps.submitted': submitted})
                r = self.db.task.update_one({'_id': ObjectId(task_id)}, {'$set': update})
                if r.modified_count:
                    self.add_op_log('save_%s_%s' % (mode, task_type), context=task_id)

            # 提交任务
            if mode == 'do' and data.get('submit') and data['step'] == steps_todo[-1]:
                ret.update(self.finish_task(task))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveCutEditApi(FinishTaskApi):
    URL = '/api/data/cut_edit/@doc_id'

    def post(self, doc_id):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
        try:
            # 检查参数
            data = self.get_request_data()
            rules = [(v.not_empty, 'step', 'boxes')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            page = self.db.page.find_one({'name': doc_id})
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
            r = self.db.page.update_one({'name': doc_id}, {'$set': {data_field: json_decode(data['boxes'])}})
            if r.modified_count:
                self.add_op_log('save_edit_%s' % data_field, context=doc_id)
            self.send_data_response({'updated': True})

        except DbError as e:
            self.send_db_error(e)
