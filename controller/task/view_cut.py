#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

import re
import controller.errors as errors
from controller.task.base import TaskHandler
from controller.data.api_algorithm import GenerateCharIdApi as GenApi


class CutHandler(TaskHandler):
    URL = ['/task/@cut_type/@page_name',
           '/task/do/@cut_type/@page_name',
           '/task/update/@cut_type/@page_name',
           '/data/(cut_edit)/@page_name']

    steps = {
        '1': {'name': 'char_box', 'name_zh': '字框', 'field': 'chars'},
        '2': {'name': 'block_box', 'name_zh': '栏框', 'field': 'blocks'},
        '3': {'name': 'column_box', 'name_zh': '列框', 'field': 'columns'},
        '4': {'name': 'char_order', 'name_zh': '字序', 'field': 'chars'},
    }

    def get(self, task_type, page_name):
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            step = self.get_query_argument('step', '') or self.prop(page, 'tasks.%s.steps.current' % task_type) or '1'
            if not re.match(r'\d+', step) or int(step) < 1 or int(step) > len(self.steps.keys()):
                self.send_error_response(errors.task_step_error, render=True)

            mode = (re.findall('(do|update|edit)/', self.request.path) or ['view'])[0]
            readonly = mode == 'view' or not self.check_auth(mode, page, task_type)
            data_field = self.steps[step]['field']
            boxes = self.prop(page, data_field)
            box_type = data_field.split('.')[-1].rstrip('s'),
            steps_todo = self.prop(page, 'tasks.%s.steps.todo') or ['']
            is_first_step, is_last_step = step == steps_todo[0], step == steps_todo[-1]
            sub_title = '%s.%s' % (step, self.steps[step]['name_zh'])
            template = 'task_char_order.html' if step == '4' else 'task_cut_do.html'
            kwargs = self.char_render(page, int(self.get_query_argument('layout', 0)), **{}) if step == '4' else {}
            self.render(
                template, page=page, task_type=task_type, readonly=readonly, mode=mode, name=page['name'],
                box_version=1, boxes=boxes, box_type=box_type, sub_title=sub_title,
                is_first_step=is_first_step, is_last_step=is_last_step,
                get_img=self.get_img, **kwargs
            )

        except Exception as e:
            self.send_db_error(e, render=True)

    @classmethod
    def char_render(cls, page, layout, **kwargs):
        """ 生成字序编号 """
        need_ren = GenApi.get_invalid_char_ids(page['chars']) or layout and layout != page.get('layout_type')
        if need_ren:
            page['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], page['layout_type'], kwargs['chars_col'] = GenApi.sort(
            page['chars'], page['columns'], page['blocks'], layout or page.get('layout_type'))
        return kwargs
