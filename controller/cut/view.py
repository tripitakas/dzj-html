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
from controller.data.api_algorithm import GenerateCharIdApi as GenApi


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
        need_ren = GenApi.get_invalid_char_ids(page['chars']) or layout and layout != page.get('layout_type')
        if need_ren:
            page['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], page['layout_type'], kwargs['chars_col'] = GenApi.sort(
            page['chars'], page['columns'], page['blocks'], layout or page.get('layout_type'))
        return kwargs
