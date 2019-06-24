#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

from controller import errors
from controller.task.base import TaskHandler
from controller.data.api_algorithm import GenerateCharIdApi as GenApi


class CutBaseHandler(TaskHandler):
    def enter(self, box_type, stage, name, mode='view', **kwargs):
        try:
            task_type = '%s_cut_%s' % (box_type, stage)
            data_type = self.get_data_type(task_type)
            page = self.db.page.find_one(dict(name=name), self.simple_fileds(include=[data_type]))
            if not page:
                return self.render('_404.html')

            # 检查任务分配权限
            task_field = 'tasks.' + task_type
            if self.prop(page, task_field + '.picked_user_id') != self.current_user['_id']:
                return self.send_error_response(errors.task_unauthorized, render=True, reason=name)

            # 检查任务状态是否为已领取或已完成（已退回的任务没有权限）
            if self.prop(page, task_field + '.status') not in [self.STATUS_PICKED, self.STATUS_FINISHED]:
                return self.send_error_response(errors.task_unauthorized, render=True, reason=name)

            # 检查数据锁（已完成后没有数据锁，需要重新申请）
            readonly = True
            if mode in ['do', 'edit']:
                if self.has_data_lock(name, data_type) or self.get_data_lock(name, data_type) is True:
                    readonly = False

            kwargs = self.char_render(self, page, **kwargs) if box_type == 'char' else kwargs
            template_name = kwargs.pop('template_name', 'task_cut_detail.html')
            self.render(
                template_name, page=page, name=page['name'], boxes=page[data_type], get_img=self.get_img,
                data_type=data_type, task_type=task_type, box_type=box_type, readonly=readonly, mode=mode,
                **kwargs
            )

        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def char_render(self, p, **kwargs):
        layout = int(self.get_query_argument('layout', 0))
        need_ren = GenApi.get_invalid_char_ids(p['chars']) or layout and layout != p.get('layout_type')
        if need_ren:
            p['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], p['layout_type'], kwargs['chars_col'] = GenApi.sort(
            p['chars'], p['columns'], p['blocks'], layout or p.get('layout_type'))
        return kwargs


class CutProofHandler(CutBaseHandler):
    URL = ['/task/do/@box_type_cut_proof/@page_name', '/task/@box_type_cut_proof/@page_name']

    def get(self, box_type, page_name):
        """ 进入切分校对页面 """
        mode = 'do' if '/do' in self.request.path else 'view'
        self.enter(box_type, 'proof', page_name, mode=mode)


class CutReviewHandler(CutBaseHandler):
    URL = ['/task/do/@box_type_cut_review/@page_name', '/task/@box_type_cut_review/@page_name']

    def get(self, box_type, page_name):
        """ 进入切分校对页面 """
        mode = 'do' if '/do' in self.request.path else 'view'
        self.enter(box_type, 'review', page_name, mode=mode)


class CharOrderProofHandler(CutBaseHandler):
    URL = ['/task/do/char_order_proof/@page_name', '/task/char_order_proof/@page_name']

    def get(self, page_name):
        """ 进入字序校对页面 """
        mode = 'do' if '/do' in self.request.path else 'view'
        self.enter('char', 'proof', page_name, mode=mode, template_name='task_char_order.html')


class CutEditHandler(CutBaseHandler):
    URL = '/task/edit/(blocks|columns|chars)/@page_name'

    data_names = {
        'blocks': '切栏数据',
        'columns': '切列数据',
        'chars': '切字数据',
    }

    def get(self, data_type, page_name):
        """ 进入数据编辑页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name), self.simple_fileds(include=[data_type]))
            if not page:
                return self.render('_404.html')

            # 检查数据锁
            readonly = True
            if self.has_data_lock(page_name, data_type) or self.get_data_lock(page_name, data_type) is True:
                readonly = False

            if data_type == 'chars':
                self.char_render(self, page)

            task_type = 'edit_' + data_type

            self.render(
                'task_cut_edit.html', page=page, name=page['name'], boxes=page[data_type], get_img=self.get_img,
                data_type=data_type, task_type=task_type, box_type=data_type[:-1], readonly=readonly, mode='edit',
                data_names=self.data_names,
            )

        except Exception as e:
            self.send_db_error(e, render=True)
