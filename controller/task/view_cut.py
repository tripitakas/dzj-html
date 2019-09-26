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
        'char_box': {'name': '字框', 'field': 'chars', 'template': 'task_cut_do.html'},
        'block_box': {'name': '栏框', 'field': 'blocks', 'template': 'task_cut_do.html'},
        'column_box': {'name': '列框', 'field': 'columns', 'template': 'task_cut_do.html'},
        'char_order': {'name': '字序', 'field': 'chars', 'template': 'task_char_order.html'},
    }

    def get(self, task_type, page_name):
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            cur_step = self.get_query_argument('step', '')
            steps = self.prop(page, 'tasks.%s.steps' % task_type)
            mode = (re.findall('(do|update|edit)/', self.request.path) or ['view'])[0]
            if not cur_step:
                if mode == 'do':
                    submitted = self.prop(page, 'tasks.%s.steps.submitted') or []
                    un_submitted = [s for s in steps['todo'] if s not in submitted]
                    if not un_submitted:
                        return self.send_error_response(errors.task_finished_not_allowed_do, render=True)
                    cur_step = un_submitted[0]
                else:
                    cur_step = steps['todo'][0]
            elif cur_step not in steps['todo']:
                return self.send_error_response(errors.task_step_error, render=True)

            index = steps['todo'].index(cur_step)
            steps['current'] = cur_step
            steps['is_first'] = index == 0
            steps['is_last'] = index == len(steps['todo']) - 1
            steps['prev'] = steps['todo'][index - 1] if index > 0 else None
            steps['next'] = steps['todo'][index + 1] if index < len(steps['todo']) - 1 else None

            readonly = mode == 'view' or not self.check_auth(mode, page, task_type)
            data_field = self.steps[cur_step]['field']
            boxes = self.prop(page, data_field)
            box_type = data_field.split('.')[-1].rstrip('s')
            sub_title = self.steps[cur_step]['name']
            layout = int(self.get_query_argument('layout', 0))
            kwargs = self.char_render(page, layout, **{}) if cur_step == 'char_order' else {}
            self.render(
                self.steps[cur_step]['template'], page=page, task_type=task_type, readonly=readonly, mode=mode,
                name=page['name'], box_version=1, boxes=boxes, box_type=box_type, sub_title=sub_title,
                get_img=self.get_img, steps=steps, **kwargs
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
