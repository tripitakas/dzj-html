#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务工作页面
@time: 2018/12/26
"""

import json
from os import path
from controller import errors
from controller.task.base import TaskHandler


class CutDetailBaseHandler(TaskHandler):
    def enter(self, box_type, stage, name):
        def handle_response(body):
            try:
                page = self.db.page.find_one(dict(name=name))
                if not page:
                    return self.render('_404.html')

                if not body.get('name') and not readonly:  # 锁定失败
                    return self.send_error_response(errors.task_locked, render=True, reason=name)

                from_url = self.get_query_argument('from', None)
                self.render('task_cut_detail.html', page=page, name=page['name'], readonly=readonly,
                            boxes=page[box_type + 's'],
                            title=task_name + ('校对' if stage == 'proof' else '审定'),
                            get_img=self.get_img,
                            from_url=from_url or '/task/lobby/' + task_type,
                            can_return=from_url,
                            box_type=box_type, stage=stage, task_type=task_type, task_name=task_name)
            except Exception as e:
                self.send_db_error(e, render=True)

        task_type = '%s_cut_%s' % (box_type, stage)
        task_name = '%s切分' % dict(block='栏', column='列', char='字')[box_type]
        readonly = self.get_query_argument('view', 0)
        if readonly:
            handle_response({})
        else:
            self.call_back_api('/api/task/pick/{0}/{1}'.format(task_type, name), handle_response)

    def get_img(self, name):
        cfg = self.application.config
        if 'page_codes' not in cfg:
            try:
                cfg['page_codes'] = json.load(open(path.join(self.application.BASE_DIR, 'page_codes.json')))
            except OSError:
                cfg['page_codes'] = {}
        code = cfg['page_codes'].get(name)
        if code:
            base_url = 'http://tripitaka-img.oss-cn-beijing.aliyuncs.com/page'
            sub_dirs = '/'.join(name.split('_')[:-1])
            url = '/'.join([base_url, sub_dirs, name + '_' + code + '.jpg'])
            return url + '?x-oss-process=image/resize,m_lfit,h_300,w_300'

        return '/static/img/{0}/{1}.jpg'.format(name[:2], name)


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


class CharProofDetailHandler(TaskHandler):
    URL = '/task/do/text_proof/@num/@task_id'

    def get(self, proof_num, name=''):
        """ 进入文字校对页面 """
        try:
            page = self.db.page.find_one(dict(name=name)) or dict(name='?')
            if not page:
                return self.render('_404.html')
            self.render('text_proof.html', page=page,
                        readonly=page.get('text_proof_user') != self.current_user['_id'])
        except Exception as e:
            self.send_db_error(e, render=True)


class CharReviewDetailHandler(TaskHandler):
    URL = '/task/do/text_review/@num/@task_id'

    def get(self, name=''):
        """ 进入文字审定页面 """
        try:
            page = self.db.page.find_one(dict(name=name)) or dict(name='?')
            if not page:
                return self.render('_404.html')
            self.render('text_review.html', page=page,
                        readonly=page.get('text_proof_user') != self.current_user['_id'])
        except Exception as e:
            self.send_db_error(e, render=True)
