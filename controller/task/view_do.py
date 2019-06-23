#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

from controller import errors
from controller.task.base import TaskHandler
from controller.data.api_algorithm import GenerateCharIdApi as GenApi


class CutDetailBaseHandler(TaskHandler):
    def enter(self, box_type, stage, name, **kwargs):
        def handle_response(body):
            try:
                page = self.db.page.find_one(dict(name=name))
                if not page:
                    return self.render('_404.html')

                if not body.get('name') and not readonly:  # 锁定失败
                    return self.send_error_response(errors.task_locked, render=True, reason=name)

                kwargs2 = self.char_render(self, page, task_type, **kwargs) if box_type == 'char' else kwargs
                template_name = kwargs2.pop('template_name', 'task_cut_detail.html')
                self.render(template_name, page=page, name=page['name'], readonly=readonly,
                            boxes=page[box_type + 's'],
                            title=task_name + ('校对' if stage == 'proof' else '审定'),
                            get_img=self.get_img,
                            from_url=from_url or '/task/lobby/' + task_type,
                            can_return=from_url,
                            box_type=box_type, stage=stage, task_type=task_type, task_name=task_name, **kwargs2)
            except Exception as e:
                self.send_db_error(e, render=True)

        task_type = '%s_cut_%s' % (box_type, stage)
        task_name = '切%s' % dict(block='栏', column='列', char='字')[box_type]
        from_url = self.get_query_argument('from', None)
        readonly = int(self.get_query_argument('view', 0)) or 'do' not in self.request.uri
        if readonly:
            handle_response({})
        else:
            pick_from = '?from=' + from_url if from_url else ''
            self.call_back_api('/api/task/pick/{0}/{1}{2}'.format(task_type, name, pick_from), handle_response)

    @staticmethod
    def char_render(self, p, task_type, **kwargs):
        layout = int(self.get_query_argument('layout', 0))
        need_ren = GenApi.get_invalid_char_ids(p['chars']) or layout and layout != p.get('layout_type')
        if need_ren:
            p['chars'][0]['char_id'] = ''  # 强制重新生成编号
        kwargs['zero_char_id'], p['layout_type'], kwargs['chars_col'] = GenApi.sort(
            p['chars'], p['columns'], p['blocks'], layout or p.get('layout_type'))

        if 'cut' not in task_type and kwargs.get('from_url', '').startswith('/task/lobby/'):
            kwargs['from_url'] = self.request.uri.replace('order', 'cut')  # 返回字切分校对
        return kwargs


class CutProofDetailHandler(CutDetailBaseHandler):
    URL = ['/task/do/@box_type_cut_proof/@page_name', '/task/@box_type_cut_proof/@page_name']

    def get(self, box_type, name):
        """ 进入切分校对页面 """
        self.enter(box_type, 'proof', name)


class CutReviewDetailHandler(CutDetailBaseHandler):
    URL = ['/task/do/@box_type_cut_review/@page_name', '/task/@box_type_cut_review/@page_name']

    def get(self, box_type, name):
        """ 进入切分审定页面 """
        self.enter(box_type, 'review', name)


class CharOrderProofHandler(CutDetailBaseHandler):
    URL = ['/task/do/char_order_proof/@page_name', '/task/char_order_proof/@page_name']

    def get(self, name):
        """ 进入字序校对页面 """
        self.enter('char', 'proof', name, template_name='task_char_order.html')
