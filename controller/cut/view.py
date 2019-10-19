#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 切分页面。
切分页面有几种访问方式：
1. 切分任务工作页面。任务用户通过do/update模式进行工作。管理员通过view模式查看任务现场。
2. 切分数据查看、修改页面。所有人可以通过view模式访问数据查看页面。有资质的用户可以通过edit模式访问数据修改页面。
由于数据共享的需求，有以下场景比较复杂：
1. 任务用户update时，已被其他人锁定。此时用户仍然可以进入update页面，提示数据已被锁定。
2. 有资质的用户edit时，已被其他人锁定。此时用户仍然可以进入edit页面，提示数据已被锁定。
设计以下几个参数区分多种场景：
1. mode，包括do/update/edit/view
2. readonly，实际就是是否有数据锁，有则可写，无则只读
3. qualified，是否有申请数据锁的资质
不能访问页面的几种情况：
1. 访问do和update页面时，没有任务权限
2. 访问edit页面时，没有数据资质
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
            self.check_task_auth(task, mode)
            has_lock = self.check_task_lock(task, mode) is True
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))
            box_type = re.findall('(char|column|block)', steps['current'])[0]
            boxes = page.get(box_type + 's')
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                kwargs = self.char_render(page, int(self.get_query_argument('layout', 0)), **kwargs)
                template = 'task_char_order.html'

            self.render(
                template, task=task, task_type=task_type, page=page, readonly=not has_lock, mode=mode,
                steps=steps, boxes=boxes, box_type=box_type,
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
    URL = '/data/edit/box/@page_name'

    def get(self, page_name):
        """ 切分框查看和修改页面"""

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 获取数据锁
            r = self.get_data_lock(page_name, 'box')
            if r is not True:
                return self.send_error_response(r, render=True)

            # 设置当前步骤
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
                kwargs = CutHandler.char_render(page, int(self.get_query_argument('layout', 0)), **kwargs)
                template = 'task_char_order.html'

            self.render(
                template, task_type='', task=dict(), page=page, steps=steps, readonly=False, mode='edit',
                boxes=boxes, box_type=box_type, get_img=self.get_img, **kwargs
            )

        except Exception as e:
            return self.send_db_error(e, render=True)
