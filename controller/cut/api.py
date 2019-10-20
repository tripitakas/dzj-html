#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
from datetime import datetime
from tornado.escape import json_decode
from bson.objectid import ObjectId
from .sort import Sort
import controller.validate as v
import controller.errors as errors
from controller.base import BaseHandler, DbError
from controller.task.base import TaskHandler


class CutApi(TaskHandler):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    step_field_map = dict(char_box='chars', block_box='blocks', column_box='columns', char_order='chars')

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
                return self.send_error_response(errors.task_un_existed)
            steps_todo = self.prop(task, 'steps.todo')
            if not data['step'] in steps_todo:
                return self.send_error_response(errors.task_step_error)

            # 检查任务权限及数据锁
            mode = 'do' if 'do/' in self.request.path else 'update'
            self.check_task_auth(task, mode)
            r = self.check_task_lock(task, mode)
            if r is not True:
                return self.send_error_response(r)

            # 保存数据
            collection, id_name = self.get_task_meta(task_type)[:2]
            update = {self.step_field_map.get(data['step']): json_decode(data['boxes'])}
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
            if data.get('submit') and data['step'] == steps_todo[-1]:
                if mode == 'do':
                    self.finish_task(task)
                    self.add_op_log('submit_%s_%s' % (mode, task_type), context=task_id)
                else:
                    self.release_temp_lock(task['doc_id'], shared_field='box')

            return self.send_data_response()

        except DbError as e:
            return self.send_db_error(e)


class CutEditApi(TaskHandler):
    URL = '/api/data/edit/box/@page_name'

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
                return self.send_error_response(errors.no_object)
            if not data['step'] in CutApi.step_field_map:
                return self.send_error_response(errors.task_step_error)

            # 检查数据锁
            if not self.has_data_lock(page_name, 'box'):
                return self.send_error_response(errors.data_unauthorized)

            # 保存数据
            step_data_field = CutApi.step_field_map.get(data['step'])
            r = self.db.page.update_one({'name': page_name}, {'$set': {step_data_field: json_decode(data['boxes'])}})
            if r.modified_count:
                self.add_op_log('save_edit_%s' % step_data_field, context=page_name)

            # 释放数据锁
            if data.get('submit'):
                self.release_temp_lock(page_name, shared_field='box')

            return self.send_data_response()

        except DbError as e:
            return self.send_db_error(e)


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
        if chars_col:
            assert isinstance(chars_col, list) and isinstance(chars_col[0], list) and isinstance(chars_col[0][0], int)

        if reorder.get('blocks'):
            blocks = Sort.sort_blocks(blocks)
        if reorder.get('columns') and blocks:
            columns = Sort.sort_columns(columns, blocks)

        zero_char_id, layout_type = [], data.get('layout_type')
        if reorder.get('chars') and chars:
            zero_char_id, layout_type, chars_col = Sort.sort(chars, columns, blocks, layout_type, chars_col)

        return self.send_data_response(dict(blocks=blocks, columns=columns, chars=chars, chars_col=chars_col,
                                            zero_char_id=zero_char_id, layout_type=layout_type))
