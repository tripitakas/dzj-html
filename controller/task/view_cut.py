#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

import re
from controller.task.base import TaskHandler
from controller.data.api_algorithm import GenerateCharIdApi as GenApi


class CutBaseHandler(TaskHandler):

    def enter(self, box_type, stage, name, **kwargs):
        try:
            task_type = '%s_cut_%s' % (box_type, stage)
            data_field = self.get_shared_data_field(task_type)

            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.render('_404.html')

            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            if '/task/do/char_cut' in self.request.path and 'order' not in self.request.path \
                    and self.prop(page, 'tasks.%s.committed' % task_type):
                self.redirect('/task/do/%s/order/%s' % (task_type, name))
            readonly = not self.check_auth(mode, page, task_type)
            layout = int(self.get_query_argument('layout', 0))
            kwargs = self.char_render(page, layout, **kwargs) if box_type == 'char' else kwargs
            template_name = kwargs.pop('template_name', 'task_cut_do.html')
            self.render(
                template_name, page=page, name=page['name'], boxes=page[data_field], get_img=self.get_img,
                data_field=data_field, task_type=task_type, box_type=box_type, readonly=readonly, mode=mode,
                box_version=1, **kwargs
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
        self.enter(box_type, 'proof', page_name)


class CutReviewHandler(CutBaseHandler):
    URL = ['/task/@box_type_cut_review/@page_name',
           '/task/do/@box_type_cut_review/@page_name',
           '/task/update/@box_type_cut_review/@page_name']

    def get(self, box_type, page_name):
        """ 进入切分审定页面 """
        self.enter(box_type, 'review', page_name)


class CharOrderProofHandler(CutBaseHandler):
    URL = ['/task/char_cut_proof/order/@page_name',
           '/task/do/char_cut_proof/order/@page_name',
           '/task/update/char_cut_proof/order/@page_name',
           '/data/edit/char_order/@page_name']

    def get(self, page_name):
        """ 进入字序校对页面 """
        self.enter('char', 'proof', page_name, template_name='task_char_order.html')


class CharOrderReviewHandler(CutBaseHandler):
    URL = ['/task/char_cut_review/order/@page_name',
           '/task/do/char_cut_review/order/@page_name',
           '/task/update/char_cut_review/order/@page_name']

    def get(self, page_name):
        """ 进入字序审定页面 """
        self.enter('char', 'review', page_name, template_name='task_char_order.html')