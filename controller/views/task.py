#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 任务管理、任务大厅和我的任务
@time: 2018/12/26
"""

import re
import json
import random
from os import path
from tornado.web import authenticated
from controller.handler.task import TaskHandler
from controller.helper import convert_bson
import model.user as u



class TaskLobbyHandler(TaskHandler):
    URL = '/task/lobby/@task_type'

    @authenticated
    def get(self, task_type):
        """ 任务大厅 """

        def pack(tasks, task_type):
            for t in tasks:
                if t.get(task_type, {}).get('priority'):
                    t['priority'] = t.get(task_type, {}).get('priority')
                    t['pick_url'] = '/task/pick/%s/%s' % (task_type, t['name'])
                    continue
                for k, v in t.get(task_type, {}).items():
                    if v.get('status') == self.STATUS_OPENED:
                        t['priority'] = v.get('priority')
                        t['pick_url'] = '/task/pick/%s/%s' % (task_type, t['name'])
                        continue

        try:
            tasks = list(self.get_tasks_info(task_type, self.STATUS_OPENED))
            pack(tasks, task_type)
            task_name = self.task_types[task_type]['name']
            self.render('task_lobby.html', tasks=tasks, task_type=task_type, task_name=task_name)
        except Exception as e:
            self.send_db_error(e, render=True)

class TaskAdminHandler(TaskHandler):
    URL = '/task/admin/@task_type'

    @authenticated
    def get(self, task_type):
        """ 任务管理 """

        try:
            tasks = list(self.get_tasks_info(task_type))
            task_name = self.task_types[task_type]['name']
            has_sub_tasks = 'sub_task_types' in self.task_types[task_type]

            self.render('task_admin.html',
                        tasks=tasks, task_type=task_type, task_name=task_name, has_sub_tasks=has_sub_tasks,
                        task_type_names=self.task_types, task_status_names=self.task_statuses)
        except Exception as e:
            self.send_db_error(e, render=True)


def get_my_or_free_tasks(self, task_type, max_count=12):
    """ 查找未领取或自己未完成的任务 """
    assert re.match(u.re_task_type, task_type)
    task_user = task_type + '_user'
    task_status = task_type + '_status'
    org_pages = pages = list(self.db.page.find({
        '$or': [
            {task_user: None, '$or': [{task_status: u.STATUS_OPENED}, {task_status: u.STATUS_RETURNED}]},
            {task_user: self.current_user.id, task_status: u.STATUS_LOCKED}],
    }))

    # 交叉审核、背靠背校对
    if task_type == 'text_proof_2':
        pages = [p for p in pages if p.get('text_proof_1_user') != self.current_user.id]
    elif task_type == 'text_proof_3':
        pages = [p for p in pages if p.get('text_proof_1_user') != self.current_user.id and
                 p.get('text_proof_2_user') != self.current_user.id]
    elif task_type == 'text_review':
        pages = [p for p in pages if p.get('text_proof_1_user') != self.current_user.id and
                 p.get('text_proof_2_user') != self.current_user.id and
                 p.get('text_proof_3_user') != self.current_user.id]
    elif 'review' in task_type:
        pages = [p for p in pages if p.get(task_user.replace('review', 'proof')) != self.current_user.id]

    random.shuffle(pages)
    pages = [p for p in pages if p.get(task_user)] + [p for p in pages if not p.get(task_user)]
    return pages, pages[: int(self.get_argument('count', max_count))], [p for p in org_pages if p not in pages]


def get_my_tasks(self, task_type, cond=None):
    """ 查找自己领取的任务 """
    assert re.match(u.re_task_type, task_type)
    cond = {task_type + '_status': u.STATUS_OPENED} if cond is None else cond
    cond[task_type + '_user'] = self.current_user.id
    return [convert_bson(p) for p in self.db.page.find(cond)]


class ChooseCutProofHandler(TaskHandler):
    URL = '/dzj_cut.html'

    @authenticated
    def get(self):
        """ 任务大厅-切分校对 """
        try:
            all_pages, all_tasks, all_excludes = [], [], []
            for task_type in ['block_cut_proof', 'column_cut_proof', 'char_cut_proof']:
                pages, tasks, excludes = get_my_or_free_tasks(self, task_type)
                task_name = '切%s' % (dict(block='栏', column='列', char='字')[task_type.split('_')[0]],)
                tasks = [dict(name=p['name'], kind=task_name, task_type=task_type,
                              priority=p.get(task_type + '_priority', '高'),
                              status='待继续' if p.get(task_type + '_user') else
                              u.task_statuses.get(p.get(task_type + '_status')) or '待领取') for p in tasks]
                all_pages.extend(pages)
                all_tasks.extend(tasks)
                all_excludes.extend(excludes)
            self.render('dzj_cut.html', stage='proof', tasks=all_tasks,
                        remain=len(all_pages), excludes=len(all_excludes))
        except Exception as e:
            self.send_db_error(e, render=True)

class ChooseCutReviewHandler(TaskHandler):
    URL = '/dzj_cut_check.html'

    @authenticated
    def get(self):
        """ 任务大厅-切分审定 """
        try:
            all_pages, all_tasks, all_excludes = [], [], []
            for task_type in ['block_cut_review', 'column_cut_review', 'char_cut_review']:
                pages, tasks, excludes = get_my_or_free_tasks(self, task_type)
                task_name = '切%s' % (dict(block='栏', column='列', char='字')[task_type.split('_')[0]],)
                tasks = [dict(name=p['name'], kind=task_name, task_type=task_type,
                              priority=p.get(task_type + '_priority', '高'),
                              status='待继续' if p.get(task_type + '_user') else
                              u.task_statuses.get(p.get(task_type + '_status')) or '待领取') for p in tasks]
                all_pages.extend(pages)
                all_tasks.extend(tasks)
                all_excludes.extend(excludes)
            self.render('dzj_cut.html', stage='review', tasks=all_tasks,
                        remain=len(all_pages), excludes=len(all_excludes))
        except Exception as e:
            self.send_db_error(e, render=True)


class ChooseCharProofHandler(TaskHandler):
    URL = ['/dzj_char.html', '/dzj_chars']

    @authenticated
    def get(self):
        """ 任务大厅-文字校对 """
        try:
            stage, field = '校一', 'text_proof_1'
            pages, tasks, excludes = get_my_or_free_tasks(self, 'text_proof_1')
            if not tasks:
                pages, tasks, excludes = get_my_or_free_tasks(self, 'text_proof_2')
                stage, field = '校二', 'text_proof_2'
            if not tasks:
                pages, tasks, excludes = get_my_or_free_tasks(self, 'text_proof_3')
                stage, field = '校三', 'text_proof_3'
            tasks = [dict(name=p['name'], stage=stage, proof_field=field,
                          priority=p.get(field + '_priority', '高'),
                          status='待继续' if p.get(field + '_user') else '待领取') for p in tasks]
            self.render('dzj_char.html', tasks=tasks, remain=len(pages), excludes=len(excludes))
        except Exception as e:
            self.send_db_error(e, render=True)


class ChooseCharReviewHandler(TaskHandler):
    URL = '/dzj_char_check.html'

    @authenticated
    def get(self):
        """ 任务大厅-文字校对审定 """
        try:
            pages, tasks, excludes = get_my_or_free_tasks(self, 'text_review')
            tasks = [dict(name=p['name'],
                          priority=p.get('text_review_priority', '高'),
                          status='待继续' if p.get('text_review_user') else '待领取') for p in tasks]
            self.render('dzj_char_check.html', tasks=tasks, remain=len(pages), excludes=len(excludes))
        except Exception as e:
            self.send_db_error(e, render=True)


class MyTasksHandler(TaskHandler):
    URL = '/dzj_@task-kind_history.html'

    @authenticated
    def get(self, kind):
        """ 我的任务 """
        try:
            def fetch(a_type, kind_name):
                items = get_my_tasks(self, a_type, {})
                for r in items:
                    r['kind_name'] = kind_name  # 用于过滤列表项
                    r['current_task'] = a_type  # 用于拼字段名
                kinds.append(kind_name)
                return items

            task_types = dict(char='text_proof', char_check='text_review',
                              hard='hard_proof', hard_check='hard_review',
                              cut='cut_proof', cut_check='cut_review',
                              fmt='fmt_proof', fmt_check='fmt_review')
            assert kind in task_types
            task_type = task_types[kind]

            title = dict(char='文字校对', char_check='文字审定',
                         hard='难字校对', hard_check='难字审定',
                         cut='切分校对', cut_check='切分审定',
                         fmt='格式校对', fmt_check='格式审定')[kind]

            kinds = []
            if task_type == 'text_proof':
                pages = fetch('text_proof_3', '校三') +\
                        fetch('text_proof_2', '校二') +\
                        fetch('text_proof_1', '校一')
            elif task_type == 'cut_proof':
                pages = fetch('block_cut_proof', '切栏') +\
                        fetch('column_cut_proof', '切列') +\
                        fetch('char_cut_proof', '切字')
            elif task_type == 'cut_review':
                pages = fetch('block_cut_review', '切栏') +\
                        fetch('column_cut_review', '切列') +\
                        fetch('char_cut_review', '切字')
            else:
                pages = fetch(task_type, title)
            self.render('dzj_cut_history.html'.format(kind), pages=pages, task_type=task_type,
                        kind=kind, kinds=kinds, title=title)
        except Exception as e:
            self.send_db_error(e, render=True)


class CutProofDetailHandler(TaskHandler):
    URL = '/dzj_@box-type_cut_(proof|review)/@task_id'

    @authenticated
    def get(self, box_type, stage, name):
        """ 进入切分校对 """

        def handle_response(body):
            try:
                page = convert_bson(self.db.page.find_one(dict(name=name)))
                if not page:
                    return self.render('_404.html')

                self.render('dzj_cut_detail.html', page=page,
                            readonly=body.get('name') != name,
                            title='切分校对' if stage == 'proof' else '切分审定',
                            get_img=self.get_img,
                            box_type=box_type, stage=stage, task_type=task_type, task_name=task_name)
            except Exception as e:
                self.send_db_error(e, render=True)

        task_type = '%s_cut_%s' % (box_type, stage)
        task_name = '%s切分' % dict(block='栏', column='列', char='字')[box_type]
        self.call_back_api('/api/pick/{0}/{1}'.format(task_type, name), handle_response)

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


class CharProofDetailHandler(TaskHandler):
    URL = ['/dzj_char_detail.html', '/dzj_char/@task_id']

    @authenticated
    def get(self, name=''):
        """ 进入文字校对 """
        try:
            page = convert_bson(self.db.page.find_one(dict(name=name))) or dict(name='?')
            if not page:
                return self.render('_404.html')
            self.render('dzj_char_detail.html', page=page,
                        readonly=page.get('text_proof_user') != self.current_user.id)
        except Exception as e:
            self.send_db_error(e, render=True)


class CutStatusHandler(TaskHandler):
    URL = '/dzj_task_cut_status.html'

    @authenticated
    def get(self):
        """ 任务管理-切分状态 """

        def handle_response(body):
            self.render('dzj_task_cut_status.html',
                        status_cls=CutStatusHandler.status_cls,
                        status_desc=CutStatusHandler.status_desc,
                        sum_status=CutStatusHandler.sum_status, **body)

        self.call_back_api('/api/pages/cut_status', handle_response)

    @staticmethod
    def status_desc(page, prefix):
        status = page.get(prefix + '_status')
        return u.task_statuses.get(status)

    @staticmethod
    def status_cls(page, prefix):
        return 'status_' + page.get(prefix + '_status', 'none')

    @staticmethod
    def sum_status(pages, prefix):
        values = []
        for p in pages:
            v = CutStatusHandler.status_desc(p, prefix)
            if v not in values:
                values.append(v)
        return values


class TextStatusHandler(TaskHandler):
    URL = '/dzj_task_char_status.html'

    @authenticated
    def get(self):
        """ 任务管理-文字状态 """

        def handle_response(body):
            self.render('dzj_task_char_status.html',
                        status_cls=CutStatusHandler.status_cls,
                        status_desc=CutStatusHandler.status_desc,
                        sum_status=CutStatusHandler.sum_status, **body)

        self.call_back_api('/api/pages/text_status', handle_response)
