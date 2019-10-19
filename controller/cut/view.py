#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

import re
from bson.objectid import ObjectId
import controller.errors as errors
from controller.task.base import TaskHandler
from .sort import Sort
from .api import CutApi


class CutHandler(TaskHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对页面 """
        try:
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.render('_404.html')
            page = self.db.page.find_one({task['id_name']: task['doc_id']})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            mode = (re.findall('(do|update)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(task, mode)
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))
            box_type = re.findall('(char|column|block)', steps['current'])[0]
            boxes = page.get(box_type + 's')
            step_name = self.step_names().get(steps['current'])
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                kwargs = self.char_render(page, int(self.get_query_argument('layout', 0)), **kwargs)
                template = 'task_char_order.html'

            self.render(
                template, task_type=task_type, page=page, steps=steps, readonly=readonly, mode=mode,
                boxes=boxes, box_type=box_type, step_name=step_name,
                get_img=self.get_img, **kwargs
            )

        except Exception as e:
            self.send_db_error(e, render=True)

    @classmethod
    def char_render(cls, page, layout, **kwargs):
        """ 生成字序编号 """
        need_ren = Sort.get_invalid_char_ids(page['chars']) or layout and layout != page.get('layout_type')
        if need_ren:
            page['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], page['layout_type'], kwargs['chars_col'] = Sort.sort(
            page['chars'], page['columns'], page['blocks'], layout or page.get('layout_type'))
        return kwargs


class CutEditHandler(TaskHandler):
    URL = ['/data/edit/box/@page_name']

    def get(self, page_name):
        """ 切分修改页面 """

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 检查数据锁
            if not self.has_data_lock('page', 'name', page_name, 'box', True):
                return self.send_error_response(errors.data_unauthorized, render=True)

            # 检查当前步骤
            default_steps = list(CutApi.step_field_map.keys())
            cur_step = self.get_query_argument('step', default_steps[0])
            if cur_step not in default_steps:
                return self.send_error_response(errors.task_step_error)

            mode = 'edit'
            fake_task = dict(steps={'todo': default_steps})
            steps = self.init_steps(fake_task, mode, cur_step)
            box_type = re.findall('(char|column|block)', steps['current'])[0]
            boxes = page.get(box_type + 's')
            step_name = self.step_names().get(steps['current'])
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                kwargs = CutHandler.char_render(page, int(self.get_query_argument('layout', 0)), **kwargs)
                template = 'task_char_order.html'

            self.render(
                template, page=page, steps=steps, readonly=False, mode=mode,
                boxes=boxes, box_type=box_type, step_name=step_name,
                get_img=self.get_img, **kwargs
            )

        except Exception as e:
            return self.send_db_error(e, render=True)
