#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 切分页面。
参数及场景说明：
1. readonly，只读还是可写。用户有数据资质且申请到数据锁，则可写。否则，只读。
2. mode，包括do/update/edit/view。以下场景都是已经通过角色检查之后的情况：
 - do是做任务的模式。检查任务权限和数据锁，没有则无法访问页面。
 - update是更新任务模式。检查任务权限，没有则无法访问。进一步检查数据锁。
 - view是任务查看模式。不检查任务权限和数据锁，不能提交修改。
 - edit是数据编辑模式。检查数据锁，没有则只读。
 只读时可访问页面，但是不能提交修改。
@time: 2018/12/26
"""

import re
from bson.objectid import ObjectId
import controller.errors as errors
from controller.task.base import TaskHandler
from .cuttool import CutTool
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

            # 检查任务权限及数据锁
            mode = (re.findall('(do|update)/', self.request.path) or ['view'])[0]
            self.check_task_auth(task, mode)
            has_lock = self.check_task_lock(task, mode) is True

            # 设置步骤
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))

            box_type = re.findall('(char|column|block)', steps['current'])[0]
            boxes = page.get(box_type + 's')
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                kwargs = CutTool.char_render(page, int(self.get_query_argument('layout', 0)))
                template = 'task_char_order.html'

            self.render(
                template, task=task, task_type=task_type, page=page, readonly=not has_lock, mode=mode,
                steps=steps, boxes=boxes, box_type=box_type,
                get_img=self.get_img, **kwargs
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class CutEditHandler(TaskHandler):
    URL = '/data/edit/box/@page_name'

    def get(self, page_name):
        """ 切分框查看和修改页面"""

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 获取数据锁
            has_lock = self.get_data_lock(page_name, 'box') is True

            # 设置步骤
            default_steps = list(CutApi.step_field_map.keys())
            cur_step = self.get_query_argument('step', default_steps[0])
            if cur_step not in default_steps:
                return self.send_error_response(errors.task_step_error)
            fake_task = dict(steps={'todo': default_steps})
            steps = self.init_steps(fake_task, 'edit', cur_step)

            box_type = re.findall('(char|column|block)', steps['current'])[0]
            boxes = page.get(box_type + 's')
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                kwargs = CutTool.char_render(page, int(self.get_query_argument('layout', 0)), **kwargs)
                template = 'task_char_order.html'

            self.render(
                template, task_type='', task=dict(), page=page, steps=steps, readonly=not has_lock, mode='edit',
                boxes=boxes, box_type=box_type, get_img=self.get_img, **kwargs
            )

        except Exception as e:
            return self.send_db_error(e, render=True)
