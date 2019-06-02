#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

from controller import errors
from controller.task.base import TaskHandler
from controller.layout.v1 import calc as calc_old
from controller.layout.v2 import calc as calc_new


class CutDetailBaseHandler(TaskHandler):
    def enter(self, box_type, stage, name, **kwargs):
        def handle_response(body):
            try:
                page = self.db.page.find_one(dict(name=name))
                if not page:
                    return self.render('_404.html')

                if not body.get('name') and not readonly:  # 锁定失败
                    return self.send_error_response(errors.task_locked, render=True, reason=name)

                template_name = kwargs.pop('template_name', 'task_cut_detail.html')
                self.render(template_name, page=page, name=page['name'], readonly=readonly,
                            boxes=page[box_type + 's'],
                            title=task_name + ('校对' if stage == 'proof' else '审定'),
                            get_img=self.get_img,
                            from_url=from_url or '/task/lobby/' + task_type,
                            can_return=from_url,
                            box_type=box_type, stage=stage, task_type=task_type, task_name=task_name, **kwargs)
            except Exception as e:
                self.send_db_error(e, render=True)

        task_type = '%s_cut_%s' % (box_type, stage)
        task_name = '%s切分' % dict(block='栏', column='列', char='字')[box_type]
        from_url = self.get_query_argument('from', None)
        readonly = int(self.get_query_argument('view', 0))
        if readonly:
            handle_response({})
        else:
            pick_from = '?from=' + from_url if from_url else ''
            self.call_back_api('/api/task/pick/{0}/{1}{2}'.format(task_type, name, pick_from), handle_response)


class CutProofDetailHandler(CutDetailBaseHandler):
    URL = '/task/do/@box_type_cut_proof/@task_id'

    def get(self, box_type, name):
        """ 进入切分校对页面 """
        self.enter(box_type, 'proof', name)


class CutReviewDetailHandler(CutDetailBaseHandler):
    URL = '/task/do/@box_type_cut_review/@task_id'

    def get(self, box_type, name):
        """ 进入切分审定页面 """
        self.enter(box_type, 'review', name)


class CharOrderProofHandler(CutDetailBaseHandler):
    URL = '/task/do/char_order_proof/@task_id'

    def get(self, name):
        """ 进入字序校对页面 """
        self.enter('char', 'proof', name, template_name='task_char_order.html',
                   layout=int(self.get_query_argument('layout', 0)),
                   zero_char_id=[])

    def render(self, template_name, **kwargs):
        def get_char_no(char):
            try:
                p = char.get('char_id').split('c')
                return int(p[2])
            except TypeError:
                return 0

        if kwargs.get('layout') in [1, 2]:
            page = kwargs['page']
            chars = page['chars']
            new_chars = (calc_new if kwargs['layout'] == 2 else calc_old)(chars, page['blocks'], page['columns'])
            ids0 = {}

            for c_i, c in enumerate(new_chars):
                if not c['column_order']:
                    zero_key = 'b%dc%d' % (c['block_id'], c['column_id'])
                    ids0[zero_key] = ids0.get(zero_key, 100) + 1
                    c['column_order'] = ids0[zero_key]
                chars[c_i]['char_id'] = 'b%dc%dc%d' % (c['block_id'], c['column_id'], c['column_order'])
                chars[c_i]['block_no'] = c['block_id']
                chars[c_i]['line_no'] = c['column_id']
                chars[c_i]['char_no'] = c['column_order']
            kwargs['zero_char_id'] = [a.get('char_id') for a in chars if get_char_no(a) > 100 or not get_char_no(a)]

        if kwargs['from_url'].startswith('/task/lobby/'):
            kwargs['from_url'] = self.request.uri.replace('order', 'cut')  # 返回字切分校对

        super(CharOrderProofHandler, self).render(template_name, **kwargs)
