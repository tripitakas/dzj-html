#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
import re
from datetime import datetime
from bson.objectid import ObjectId
from .sort import Sort
from .view import CutHandler
import controller.validate as v
import controller.errors as errors
from controller.base import DbError
from tornado.escape import json_decode
from controller.base import BaseHandler
from controller.task.base import TaskHandler


class CutSaveApi(TaskHandler):
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
            collection, id_name = self.get_task_meta(task_type)[:2]
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


class CutEditSaveApi(TaskHandler):
    URL = '/api/data/edit/cut/@page_name'

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


class GenerateCharIdApi(BaseHandler):
    URL = '/api/cut/gen_char_id'

    def post(self):
        """根据坐标重新生成栏、列、字框的编号"""
        data = self.get_request_data()
        blocks = data['blocks']
        columns = data['columns']
        chars = data['chars']
        chars_col = data.get('chars_col')  # 每列字框的序号 [[char_index_of_col1, ...], col2...]
        reorder = data.get('reorder', dict(blocks=True, columns=True, chars=True))

        assert isinstance(blocks, list)
        assert isinstance(columns, list)
        assert isinstance(chars, list)
        assert not chars_col or isinstance(chars_col, list) and isinstance(chars_col[0], list) \
            and isinstance(chars_col[0][0], int)

        if reorder.get('blocks'):
            blocks = Sort.sort_blocks(blocks)
        if reorder.get('columns') and blocks:
            columns = Sort.sort_columns(columns, blocks)

        zero_char_id, layout_type = [], data.get('layout_type')
        if reorder.get('chars') and chars:
            zero_char_id, layout_type, chars_col = Sort.sort(chars, columns, blocks, layout_type, chars_col)

        self.send_data_response(dict(blocks=blocks, columns=columns, chars=chars, chars_col=chars_col,
                                     zero_char_id=zero_char_id, layout_type=layout_type))
