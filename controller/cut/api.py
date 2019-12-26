#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import json_decode
from controller import errors as e
from controller import validate as v
from controller.cut.cuttool import CutTool
from controller.cut.reorder import char_reorder
from controller.task.base import TaskHandler
from controller.base import BaseHandler, DbError


class CutTaskApi(TaskHandler):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    step2field = dict(block_box='blocks', char_box='chars', column_box='columns', char_order='chars')

    def post(self, task_type, task_id):
        """ 提交任务。有两种模式：
            1. do。做任务时，保存或提交任务。
            2. update。任务完成后，本任务用户修改数据。
        """
        try:
            # 检查参数
            data = self.get_request_data()
            rules = [(v.not_empty, 'step', 'boxes')]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                return self.send_error_response(e.task_not_existed)
            steps_todo = self.prop(task, 'steps.todo')
            if not data['step'] in steps_todo:
                return self.send_error_response(e.task_step_error)

            # 检查任务权限及数据锁
            has_auth, error = self.check_task_auth(task)
            if not has_auth:
                return self.send_error_response(error)
            has_lock, error = self.check_data_lock(task)
            if not has_lock:
                return self.send_error_response(error)

            # 字序校对时，检查连线数据
            if data['step'] == 'char_order' and data.get('link_data'):
                d = data['link_data']
                GenerateCharIdApi.calc(d['blocks'], d['columns'], d['chars'], d['chars_col'], d.get('layout_type'))
                data['boxes'] = d['chars']
                data['columns'] = d['columns']
                assert data['columns'] and data['boxes']

            # 保存数据
            page = self.db.page.find_one({task['id_name']: task['doc_id']})
            if isinstance(data['boxes'], str):
                data['boxes'] = json_decode(data['boxes'])
            self.reorder_chars(data, page)
            update = {self.step2field.get(data['step']): data['boxes']}
            if 'columns' in data:
                update['columns'] = data['columns']
            self.db.page.update_one({'name': task['doc_id']}, {'$set': update})

            # 提交任务
            if data.get('submit'):
                submitted = self.prop(task, 'steps.submitted', [])
                if data['step'] not in submitted:
                    submitted.append(data['step'])
                update = {'updated_time': datetime.now(), 'steps.submitted': submitted}
                self.db.task.update_one({'_id': ObjectId(task_id)}, {'$set': update})
                self.add_op_log('save_%s' % task_type, target_id=task_id)
                if data['step'] == steps_todo[-1]:
                    if self.get_task_mode() == 'do':
                        self.finish_task(task)
                    else:
                        self.release_temp_lock(task['doc_id'], 'box')

            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def reorder_chars(data, page):
        if data['step'] == 'char_box':
            columns = char_reorder(data['boxes'], page['blocks'])
            if columns and len(columns) != len(page['columns']):
                print(columns)
            return columns


class CutEditApi(TaskHandler):
    URL = '/api/data/edit/box/@page_name'

    def post(self, page_name):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
        try:
            # 检查参数
            data = self.get_request_data()
            steps = list(CutTaskApi.step2field.keys())
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', steps)]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            # 检查数据锁
            has_lock, error = self.check_data_lock(doc_id=page_name, shared_field='box')
            if not has_lock:
                return self.send_error_response(error)
            # 保存数据
            if isinstance(data['boxes'], str):
                data['boxes'] = json_decode(data['boxes'])
            CutTaskApi.reorder_chars(data, page)
            data_field = CutTaskApi.step2field.get(data['step'])
            self.db.page.update_one({'name': page_name}, {'$set': {data_field: data['boxes']}})
            self.add_op_log('save_edit_%s' % data_field, context=page_name, target_id=page['_id'])
            # 释放数据锁
            if data.get('submit'):
                self.release_temp_lock(page_name, 'box')
            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class GenerateCharIdApi(BaseHandler):
    URL = '/api/cut/gen_char_id'

    def post(self):
        """根据坐标重新生成栏、列、字框的编号"""
        data = self.get_request_data()
        blocks = data['blocks']
        columns = data['columns']
        chars = data['chars']
        chars_col = data.get('chars_col')  # 每列字框的序号 [[char_index_of_col1, ...], col2...]

        zero_char_id, layout_type = [], data.get('layout_type')
        r = self.calc(blocks, columns, chars, chars_col, layout_type)
        if r:
            zero_char_id, layout_type, chars_col = r

        return self.send_data_response(dict(
            blocks=blocks, columns=columns, chars=chars, chars_col=chars_col,
            zero_char_id=zero_char_id, layout_type=layout_type
        ))

    @staticmethod
    def calc(blocks, columns, chars, chars_col, layout_type=None):
        assert isinstance(blocks, list)
        assert isinstance(columns, list)
        assert isinstance(chars, list)
        reorder = dict(blocks=True, columns=True, chars=True)
        if chars_col:
            assert isinstance(chars_col, list) and isinstance(chars_col[0], list) and isinstance(chars_col[0][0], int)

        if reorder.get('blocks'):
            blocks = CutTool.sort_blocks(blocks)
        if reorder.get('columns') and blocks:
            columns = CutTool.sort_columns(columns, blocks)

        if reorder.get('chars') and chars:
            return CutTool.sort(chars, columns, blocks, layout_type, chars_col)
