#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
from .page import Page
from .base import PageHandler
from controller import helper as h
from controller import validate as v
from .api import PageBoxApi, PageOrderApi


class PageTaskPublishApi(PageHandler):
    URL = r'/api/page/task/publish'

    field_names = {
        'published': '任务已发布', 'pending': '任务已悬挂', 'finished_before': '任务已完成',
        'un_existed': '页面不存在', 'published_before': '任务曾被发布',
    }

    def post(self):
        """ 发布任务"""
        try:
            log = dict()
            self.get_page_names(log)
            rules = [
                (v.not_empty, 'page_names', 'task_type', 'priority', 'force', 'batch'),
                (v.in_list, 'task_type', list(self.task_types.keys())),
                (v.in_list, 'pre_tasks', list(self.task_types.keys())),
                (v.is_priority, 'priority'),
            ]
            self.validate(self.data, rules)
            log = self.check_and_publish(log)
            log_id = self.add_op_log(self.db, 'publish_task', None, log, self.username)
            message = '，'.join(['%s：%s条' % (self.field_names.get(k) or k, len(names)) for k, names in log.items()])
            return self.send_data_response(dict(message=message, id=str(log_id), **log))

        except self.DbError as error:
            return self.send_db_error(error)

    def get_page_names(self, log):
        """ 获取页码"""
        page_names = self.data.get('page_names')
        if page_names:
            if isinstance(page_names, str):
                page_names = page_names.split(',')
            pages = list(self.db.page.find({'name': {'$in': page_names}}, {'name': 1}))
            log['un_existed'] = set(page_names) - set([page['name'] for page in pages])
            page_names = [page['name'] for page in pages]
        names_file = self.request.files.get('names_file')
        if names_file:
            names_str = str(names_file[0]['body'], encoding='utf-8')
            try:
                page_names = json.loads(names_str)
            except json.decoder.JSONDecodeError:
                ids_str = re.sub(r'(\n|\r\n)+', ',', names_str)
                page_names = ids_str.split(r',')
            page_names = [n for n in page_names if n]
            pages = list(self.db.page.find({'name': {'$in': page_names}}, {'name': 1}))
            log['un_existed'] = set(page_names) - set([page['name'] for page in pages])
            page_names = [page['name'] for page in pages]
        elif self.data.get('prefix'):
            condition = {'name': {'$regex': self.data['prefix'], '$options': '$i'}}
            page_names = [page['name'] for page in list(self.db.page.find(condition, {'name': 1}))]
        elif self.data.get('search'):
            condition = Page.get_page_search_condition(self.data['search'])[0]
            query = self.db.page.find(condition, {'name': 1})
            page = h.get_url_param('page', self.data['search'])
            if page:
                s = h.get_url_param('page_size', self.data['search']) or self.prop(self.config, 'pager.page_size', 10)
                query = query.skip((int(page) - 1) * int(s)).limit(int(s))
            page_names = [page['name'] for page in list(query)]
        self.data['page_names'] = page_names

    def check_and_publish(self, log):
        """ 检查页码并发布任务"""
        # 去掉已发布的页码
        page_names, task_type, num = self.data['page_names'], self.data['task_type'], self.data.get('num') or 1
        if page_names:
            cond = dict(task_type=task_type, num=int(num), doc_id={'$in': list(page_names)})
            log['published_before'] = set(t['doc_id'] for t in self.db.task.find(cond, {'doc_id': 1}))
            page_names = set(page_names) - log['published_before']

        # 剩下的页码，发布新任务
        if page_names:
            pre_tasks = self.data['pre_tasks']
            if pre_tasks:
                pre_tasks = [pre_tasks] if isinstance(pre_tasks, str) else pre_tasks
                db_pre_tasks = list(self.db.task.find(
                    {'doc_id': {'$in': list(page_names)}, 'task_type': {'$in': pre_tasks}},
                    {'task_type': 1, 'num': 1, 'status': 1, 'doc_id': 1}
                ))
                # 前置任务未发布、未完成（有一个未完成，即未完成）的情况，发布为PENDING
                un_published = set(page_names) - set(t['doc_id'] for t in db_pre_tasks)
                un_finished = set(t['doc_id'] for t in db_pre_tasks if t['status'] != self.STATUS_FINISHED)
                log['pending'] = set(un_finished | un_published)
                if log['pending']:
                    self.create_tasks(log['pending'], self.STATUS_PENDING, {t: None for t in pre_tasks})
                # 其它为前置任务全部已完成的情况，发布为PUBLISHED
                page_names = set(page_names) - log['pending']
                if page_names:
                    self.create_tasks(page_names, self.STATUS_PUBLISHED, {t: self.STATUS_FINISHED for t in pre_tasks})
                    log['published'] = page_names
            else:
                self.create_tasks(page_names, self.STATUS_PUBLISHED)
                log['published'] = page_names

        return {k: list(l) for k, l in log.items() if l}

    def create_tasks(self, page_names, status, pre_tasks=None):
        def get_task(page_name, char_count=None, params=None):
            steps = self.data.get('steps') and dict(todo=self.data['steps'])
            return dict(task_type=task_type, num=int(self.data.get('num') or 1), batch=self.data['batch'],
                        collection='page', id_name='name', doc_id=page_name, char_count=char_count, status=status,
                        steps=steps, priority=int(self.data['priority']), pre_tasks=pre_tasks, params=params or {},
                        result={}, create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                        publish_user_id=self.user_id, publish_by=self.username)

        if not page_names:
            return
        task_type = self.data['task_type']
        # pages = list(self.db.page.find({'name': {'$in': list(page_names)}}, {'name': 1, 'chars': 1}))
        pages = list(self.db.page.aggregate([
            {'$match': {'name': {'$in': list(page_names)}}},
            {'$project': {'name': 1, 'char_count': {'$size': 'chars'}}}
        ]))
        if pages:
            if task_type == 'txt_match':
                tasks, fields = [], self.data.get('fields') or ['ocr_col']
                for page in pages:
                    for field in fields:
                        # field对应的文本存在且不匹配时才发布任务
                        if self.prop(page, 'txt_match.' + field) is not True and self.get_txt(page, field):
                            tasks.append(get_task(page['name'], page['char_count'], dict(field=field)))
                if tasks:
                    self.db.task.insert_many(tasks, ordered=False)
                update = {'tasks.%s.%s' % (task_type, f): status for f in fields}
                self.db.page.update_many({'name': {'$in': list(page_names)}}, {'$set': update})
            else:
                tasks = [get_task(page['name'], page['char_count']) for page in pages]
                self.db.task.insert_many(tasks, ordered=False)
                update = {'tasks.%s.%s' % (task_type, self.data.get('num') or 1): status}
                self.db.page.update_many({'name': {'$in': list(page_names)}}, {'$set': update})


class PageTaskCutApi(PageHandler):
    URL = ['/api/task/do/(cut_proof|cut_review)/@task_id',
           '/api/task/update/(cut_proof|cut_review)/@task_id']

    def post(self, task_type, task_id):
        """ 切分校对、审定页面"""
        try:
            rules = [(v.not_empty, 'step')]
            self.validate(self.data, rules)

            submitted = self.prop(self.task, 'steps.submitted') or []
            if self.data['step'] == 'box':
                update = {}
                if self.data.get('steps_finished'):
                    update['result.steps_finished'] = True
                if self.data.get('submit') and 'box' not in submitted:
                    submitted.append('box')
                    update['steps.submitted'] = submitted
                if update:
                    self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
                r = PageBoxApi.save_box(self, self.task['doc_id'], task_type)
                self.send_data_response(r)
            elif self.data['step'] == 'order':
                if self.data.get('submit') and 'order' not in submitted:
                    submitted.append('order')
                    update = {'status': self.STATUS_FINISHED, 'steps.submitted': submitted, 'finished_time': self.now()}
                    self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
                    self.update_post_tasks(self.task)
                    self.update_page_status(self.STATUS_FINISHED, self.task)
                PageOrderApi.save_order(self, self.task['doc_id'])
                self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class PageTaskTextApi(PageHandler):
    URL = ['/api/task/do/(text_proof|text_review)/@task_id',
           '/api/task/update/(text_proof|text_review)/@task_id']

    def post(self, task_type, task_id):
        """ 文字校对、审定页面"""
        try:
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': self.now()
            }})
            self.update_page_status(self.STATUS_FINISHED, self.task)
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
