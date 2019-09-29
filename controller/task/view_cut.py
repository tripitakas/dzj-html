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

    default_steps = dict(char_box='字框', block_box='栏框', column_box='列框', char_order='字序')

    def get(self, task_type, page_name):
        """ 切分校对页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            mode = (re.findall('(do|update|edit)/', self.request.path) or ['view'])[0]
            steps = self.init_steps(task_type, page, mode)

            if steps['current'] == 'char_box':
                self.char_box(task_type, page, mode, steps)
            elif steps['current'] == 'block_box':
                self.block_box(task_type, page, mode, steps)
            elif steps['current'] == 'column_box':
                self.column_box(task_type, page, mode, steps)
            else:
                self.char_order(task_type, page, mode, steps)

        except Exception as e:
            self.send_db_error(e, render=True)

    def init_steps(self, task_type, page, mode):
        """ 检查并设置step参数，有误时直接返回 """
        steps = self.prop(page, 'tasks.%s.steps' % task_type) or dict(todo=list(self.default_steps.keys()))
        current_step = self.get_query_argument('step', '')
        if not current_step:
            if mode == 'do':
                submitted = self.prop(page, 'tasks.%s.steps.submitted' % task_type) or []
                un_submitted = [s for s in steps['todo'] if s not in submitted]
                if not un_submitted:
                    return self.send_error_response(errors.task_finished_not_allowed_do, render=True)
                current_step = un_submitted[0]
            else:
                current_step = steps['todo'][0]
        elif current_step not in steps['todo']:
            return self.send_error_response(errors.task_step_error, render=True)

        index = steps['todo'].index(current_step)
        steps['current'] = current_step
        steps['is_first'] = index == 0
        steps['is_last'] = index == len(steps['todo']) - 1
        steps['prev'] = steps['todo'][index - 1] if index > 0 else None
        steps['next'] = steps['todo'][index + 1] if index < len(steps['todo']) - 1 else None
        return steps

    def char_box(self, task_type, page, mode, steps):
        readonly = not self.check_auth(mode, page, task_type)
        self.render(
            'task_cut_do.html', page=page, name=page['name'], task_type=task_type, readonly=readonly, mode=mode,
            box_version=1, boxes=page.get('chars'), box_type='char', sub_title=self.default_steps['char_box'],
            get_img=self.get_img, steps=steps
        )

    def column_box(self, task_type, page, mode, steps):
        readonly = not self.check_auth(mode, page, task_type)
        self.render(
            'task_cut_do.html', page=page, name=page['name'], task_type=task_type, readonly=readonly, mode=mode,
            box_version=1, boxes=page.get('columns'), box_type='column', sub_title=self.default_steps['column_box'],
            get_img=self.get_img, steps=steps
        )

    def block_box(self, task_type, page, mode, steps):
        readonly = not self.check_auth(mode, page, task_type)
        self.render(
            'task_cut_do.html', page=page, name=page['name'], task_type=task_type, readonly=readonly, mode=mode,
            box_version=1, boxes=page.get('blocks'), box_type='block', sub_title=self.default_steps['block_box'],
            get_img=self.get_img, steps=steps
        )

    def char_order(self, task_type, page, mode, steps):
        readonly = not self.check_auth(mode, page, task_type)
        kwargs = self.char_render(page, int(self.get_query_argument('layout', 0)), **{})
        self.render(
            'task_char_order.html', page=page, name=page['name'], task_type=task_type, readonly=readonly, mode=mode,
            box_version=1, boxes=page.get('chars'), box_type='char', sub_title=self.default_steps['char_box'],
            get_img=self.get_img, steps=steps, **kwargs
        )

    @classmethod
    def char_render(cls, page, layout, **kwargs):
        """ 生成字序编号 """
        need_ren = GenApi.get_invalid_char_ids(page['chars']) or layout and layout != page.get('layout_type')
        if need_ren:
            page['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], page['layout_type'], kwargs['chars_col'] = GenApi.sort(
            page['chars'], page['columns'], page['blocks'], layout or page.get('layout_type'))
        return kwargs


class OCRHandler(TaskHandler):
    URL = ['/task/@ocr_type/@page_name',
           '/task/do/@ocr_type/@page_name',
           '/task/update/@ocr_type/@page_name']

    def get(self, ocr_type, page_name):
        """ 进入OCR校对、审定页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(mode, page, ocr_type)
            kwargs = CutHandler.char_render(page, int(self.get_query_argument('layout', 0)), **{})
            self.render(
                'task_ocr_do.html', page=page, name=page['name'], task_type=ocr_type, readonly=readonly, mode=mode,
                box_version=1, box_type='char', boxes=page.get('chars'), get_img=self.get_img, steps=dict(),
                **kwargs
            )

        except Exception as e:
            self.send_db_error(e, render=True)
