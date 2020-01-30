#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 切分模块。参数及场景说明：
1. readonly，只读还是可写。用户有数据资质且申请到数据锁，则可写。否则，只读。
2. mode，包括do/update/edit/view。以下场景都是已经通过角色检查之后的情况：
 - do，做任务模式。检查任务权限和数据锁，没有则无法访问页面。
 - update，更新任务模式。检查任务权限，没有则无法访问。进一步检查数据锁。
 - view，任务查看模式。不检查任务权限和数据锁，不能提交修改。
 - edit，数据编辑模式。检查数据锁，没有则只读。
@time: 2018/12/26
"""

from bson import json_util
from controller import errors as e
from controller.cut.cuttool import CutTool
from controller.task.view import PageTaskHandler


class CutHandler(PageTaskHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/browse/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对页面"""
        try:
            template = 'task_cut_do.html'
            kwargs = dict()
            if self.steps['current'] == 'orders':
                kwargs = CutTool.char_render(self.page, int(self.get_query_argument('layout', 0)))
                kwargs['btn_config'] = json_util.loads(self.get_secure_cookie('%s_orders' % task_type) or '{}')
                template = 'task_char_order.html'

            self.render(template, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(PageTaskHandler):
    URL = '/data/edit/box/@page_name'

    def get_task_type(self):
        """ 重载父类函数"""
        return 'cut_proof'

    def get(self, page_name):
        """ 切分框修改页面"""
        try:
            self.page = self.db.page.find_one({'name': page_name})
            if not self.page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            # 检查数据锁
            r = self.assign_temp_lock(self.current_user, page_name, 'box')
            self.readonly, self.message = r is False, '' if r is True else str(r[1])
            self.boxes = self.page.get(self.box_type + 's')
            template = 'task_cut_do.html'
            kwargs = dict()
            if self.steps['current'] == 'orders':
                kwargs = CutTool.char_render(self.page, int(self.get_query_argument('layout', 0)))
                template = 'task_char_order.html'

            self.render(template, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CutSampleHandler(PageTaskHandler):
    URL = ['/task/sample/box',
           '/task/sample/box/@page_name']

    def get_task_type(self):
        """ 重载父类函数"""
        return 'cut_proof'

    def get(self, page_name=None):
        """ 切分校对练习页面"""
        try:
            if not page_name:
                condition = [{'$match': {'is_sample': True}}, {'$sample': {'size': 1}}]
                pages = list(self.db.page.aggregate(condition))
                if not pages:
                    return self.send_error_response(e.no_object, message='没有找到任何练习页面')
                else:
                    return self.redirect(self.request.uri.replace('/box', '/box/' + pages[0]['name']))

            self.page = self.db.page.find_one({'name': page_name})
            if not self.page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            if not self.page.get('is_sample'):
                return self.send_error_response(e.no_object, message='页面%s不是练习页面' % page_name)

            self.boxes = self.page.get(self.box_type + 's')
            self.message = '练习-' + self.page['name']
            template = 'task_cut_do.html'
            kwargs = dict()
            if self.steps['current'] == 'orders':
                template = 'task_char_order.html'
                kwargs = CutTool.char_render(self.page, int(self.get_query_argument('layout', 0)))

            self.render(template, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
