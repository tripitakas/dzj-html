#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

from controller.task.base import TaskHandler
from controller.data.api_algorithm import GenerateCharIdApi as GenApi


class CutBaseHandler(TaskHandler):

    def enter(self, box_type, stage, name, mode='view', **kwargs):
        try:
            task_type = '%s_cut_%s' % (box_type, stage)
            data_field = self.get_protected_data_field(task_type)

            page = self.db.page.find_one(dict(name=name), self.simple_fileds(include=[data_field]))
            if not page:
                return self.render('_404.html')

            readonly = self.check_auth(mode, page, task_type)
            layout = int(self.get_query_argument('layout', 0))
            kwargs = self.char_render(page, layout, **kwargs) if box_type == 'char' else kwargs
            template_name = kwargs.pop('template_name', 'task_cut_detail.html')
            self.render(
                template_name, page=page, name=page['name'], boxes=page[data_field], get_img=self.get_img,
                data_field=data_field, task_type=task_type, box_type=box_type, readonly=readonly, mode=mode,
                **kwargs
            )

        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def char_render(page, layout, **kwargs):
        need_ren = GenApi.get_invalid_char_ids(page['chars']) or layout and layout != page.get('layout_type')
        if need_ren:
            page['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], page['layout_type'], kwargs['chars_col'] = GenApi.sort(
            page['chars'], page['columns'], page['blocks'], layout or page.get('layout_type'))
        return kwargs


class CutProofHandler(CutBaseHandler):
    URL = ['/task/@box_type_cut_proof/@page_name',
           '/task/do/@box_type_cut_proof/@page_name',
           '/task/update/@box_type_cut_proof/@page_name',
           '/data/edit/@box_types/@page_name']

    def get(self, box_type, page_name):
        """ 进入切分校对页面 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update' if '/update' in p else 'edit' if '/edit' in p else 'view'
        self.enter(box_type, 'proof', page_name, mode=mode)


class CutReviewHandler(CutBaseHandler):
    URL = ['/task/@box_type_cut_review/@page_name',
           '/task/do/@box_type_cut_review/@page_name',
           '/task/update/@box_type_cut_review/@page_name']

    def get(self, box_type, page_name):
        """ 进入切分审定页面 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update' if '/update' in p else 'edit' if '/edit' in p else 'view'
        self.enter(box_type, 'review', page_name, mode=mode)


class CharOrderProofHandler(CutBaseHandler):
    URL = ['/task/char_order_proof/@page_name',
           '/task/do/char_order_proof/@page_name',
           '/task/update/char_order_proof/@page_name',
           '/data/edit/char_order/@page_name']

    def get(self, page_name):
        """ 进入字序校对页面 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update' if '/update' in p else 'edit' if '/edit' in p else 'view'
        self.enter('char', 'proof', page_name, mode=mode, template_name='task_char_order.html')
