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
from controller import errors as e
from controller.cut.api import CutTaskApi
from controller.cut.cuttool import CutTool
from controller.task.base import TaskHandler


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
                return self.send_error_response(e.no_object, message='页面%s不存在' % task['doc_id'])

            # 检查任务权限及数据锁
            has_auth, error = self.check_task_auth(task)
            if not has_auth:
                return self.send_error_response(error, message='%s(%s)' % (error[1], page['name']))
            has_lock, error = self.check_data_lock(task)
            message = '' if has_lock else str(error[1])

            mode = self.get_task_mode()
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))
            box_type = re.findall('(char|column|block)', steps['current'])[0]
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                kwargs = CutTool.char_render(page, int(self.get_query_argument('layout', 0)))
                template = 'task_char_order.html'

            self.render(
                template, task=task, task_type=task_type, page=page, readonly=not has_lock,
                mode=mode, steps=steps, box_type=box_type, boxes=page.get(box_type + 's'),
                message=message, get_img=self.get_img, **kwargs
            )

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(TaskHandler):
    URL = '/data/edit/box/@page_name'

    def get(self, page_name):
        """ 切分框查看和修改页面"""

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object)

            # 获取数据锁
            r = self.assign_temp_lock(page_name, 'box')
            has_lock, message = r is True, '' if r is True else str(r[1])

            # 设置步骤
            default_steps = list(CutTaskApi.step2field.keys())
            current_step = self.get_query_argument('step', default_steps[0])
            if current_step not in default_steps:
                return self.send_error_response(e.task_step_error)
            fake_task = dict(steps={'todo': default_steps})
            steps = self.init_steps(fake_task, 'edit', current_step)

            box_type = re.findall('(char|column|block)', steps['current'])[0]
            template = 'task_cut_do.html'
            kwargs = dict()
            if steps['current'] == 'char_order':
                template = 'task_char_order.html'
                kwargs = CutTool.char_render(page, int(self.get_query_argument('layout', 0)))

            self.render(
                template, task_type='', task=dict(), page=page, steps=steps, readonly=not has_lock,
                mode='edit', box_type=box_type, boxes=page.get(box_type + 's'),
                message=message, get_img=self.get_img, **kwargs
            )

        except Exception as error:
            return self.send_db_error(error)
