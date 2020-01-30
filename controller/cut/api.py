#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
from datetime import datetime
from bson import json_util
from bson.objectid import ObjectId
from tornado.escape import json_decode
from controller import errors as e
from controller import validate as v
from controller.cut.cuttool import CutTool
from controller.base import BaseHandler, DbError
from controller.task.view import PageTaskHandler


class CutTaskApi(PageTaskHandler):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    def post(self, task_type, task_id):
        """ 提交任务。有两种模式：1. do。做任务时，保存或提交任务。2. update。任务完成后，本任务用户修改数据"""
        try:
            data = self.get_request_data()
            steps = list(self.step2box.keys())
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', steps)]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            update = dict()
            data['boxes'] = json_decode(data['boxes']) if isinstance(data['boxes'], str) else data['boxes']
            if data['step'] == 'orders':
                assert data.get('chars_col')
                update['chars'] = CutTool.reorder_chars(data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[data['step']] = CutTool.resort(data['boxes'], data['step'], page=self.page)
            self.db.page.update_one({'name': self.task['doc_id']}, {'$set': update})

            if data.get('config'):
                self.set_secure_cookie('%s_%s' % (task_type, data['step']), json_util.dumps(data['config']))

            if data.get('submit'):
                submitted = self.prop(self.task, 'steps.submitted', [])
                if data['step'] not in submitted:
                    submitted.append(data['step'])
                update = {'updated_time': datetime.now(), 'steps.submitted': submitted}
                self.db.task.update_one({'_id': ObjectId(task_id)}, {'$set': update})
                self.add_op_log('save_%s' % task_type, target_id=task_id)
                steps_todo = self.prop(self.task, 'steps.todo', [])
                if data['step'] == steps_todo[-1]:
                    if self.mode == 'do':
                        self.finish_task(self.task)
                    else:
                        self.release_temp_lock(self.task['doc_id'], 'box', self.current_user)

            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class CutEditApi(PageTaskHandler):
    URL = '/api/data/edit/box/@page_name'

    def post(self, page_name):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
        try:
            data = self.get_request_data()
            steps = list(self.step2box.keys())
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', steps)]
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            self.page = self.db.page.find_one({'name': page_name})
            if not self.page:
                return self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            has_lock, error = self.check_data_lock(doc_id=page_name, shared_field='box')
            if not has_lock:
                return self.send_error_response(error)

            update = dict()
            data['boxes'] = json_decode(data['boxes']) if isinstance(data['boxes'], str) else data['boxes']
            if data['step'] == 'orders':
                assert data.get('chars_col')
                update['chars'] = CutTool.reorder_chars(data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[data['step']] = CutTool.resort(data['boxes'], data['step'], page=self.page)
            self.db.page.update_one({'name': self.task['doc_id']}, {'$set': update})
            self.add_op_log('edit_box', context=page_name, target_id=self.page['_id'])

            if data.get('submit'):
                self.release_temp_lock(page_name, 'box', self.current_user)

            return self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class GenerateCharIdApi(BaseHandler):
    URL = '/api/cut/gen_char_id'

    def post(self):
        """ 根据坐标重新生成栏、列、字框的编号"""
        data = self.get_request_data()
        chars = data['chars']
        blocks = data['blocks']
        columns = data['columns']
        chars_col = data.get('chars_col')  # 每列字框的序号 [[char_index_of_col1, ...], col2...]

        zero_char_id, layout_type = [], data.get('layout_type')
        r = CutTool.calc(blocks, columns, chars, chars_col, layout_type)
        if r:
            zero_char_id, layout_type, chars_col = r

        return self.send_data_response(dict(
            blocks=blocks, columns=columns, chars=chars, chars_col=chars_col,
            zero_char_id=zero_char_id, layout_type=layout_type
        ))
