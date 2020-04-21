#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import json
from os import path
from bson.objectid import ObjectId
from tornado.escape import native_str
from elasticsearch.exceptions import ConnectionTimeout
from .page import Page
from .tool.diff import Diff
from .base import PageHandler
from .tool.esearch import find_one, find_neighbor
from controller import errors as e
from controller import helper as h
from controller import validate as v
from controller.base import BaseHandler


class PageBoxApi(PageHandler):
    URL = ['/api/page/box/@page_name']

    def post(self, page_name):
        """ 提交切分校对"""
        try:
            self.save_box(self, page_name)
        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def save_box(self, page_name):
        page = self.db.page.find_one({'name': page_name})
        if not page:
            self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
        rules = [(v.not_empty, 'blocks', 'columns', 'chars')]
        self.validate(self.data, rules)
        update = self.get_box_update(self.data, page)
        self.db.page.update_one({'_id': page['_id']}, {'$set': update})
        valid, message, box_type, out_boxes = self.check_box_cover(page)
        self.send_data_response(valid=valid, message=message, box_type=box_type, out_boxes=out_boxes)
        self.add_log('update_box', target_id=page['_id'], context=page['name'])


class PageOrderApi(PageHandler):
    URL = ['/api/page/order/@page_name']

    def post(self, page_name):
        """ 提交字序校对"""
        try:
            self.save_order(self, page_name)
        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def save_order(self, page_name):
        page = self.db.page.find_one({'name': page_name})
        if not page:
            self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
        self.validate(self.data, [(v.not_empty, 'chars_col')])
        if not self.cmp_char_cid(page['chars'], self.data['chars_col']):
            return self.send_error_response(e.cid_not_identical, message='检测到字框有增减，请刷新页面')
        if len(self.data['chars_col']) != len(page['columns']):
            return self.send_error_response(e.col_not_identical, message='提交的字序中列数有变化，请检查')
        chars = self.update_char_order(page['chars'], self.data['chars_col'])
        update = dict(chars=chars, chars_col=self.data['chars_col'])
        self.db.page.update_one({'_id': page['_id']}, {'$set': update})
        self.send_data_response()
        self.add_log('update_order', target_id=page['_id'], context=page['name'])


class PageCutTaskApi(PageHandler):
    URL = ['/api/task/do/(cut_proof|cut_review)/@task_id',
           '/api/task/update/(cut_proof|cut_review)/@task_id']

    def post(self, task_type, task_id):
        """ 切分校对、审定页面"""
        try:
            print('post api')
            rules = [(v.not_empty, 'step')]
            self.validate(self.data, rules)

            submitted = self.prop(self.task, 'steps.submitted') or []
            if self.data['step'] == 'box':
                if 'box' not in submitted:
                    submitted.append('box')
                    self.db.task.update_one({'_id': self.task['_id']}, {'$set': {'steps.submitted': submitted}})
            elif self.data['step'] == 'order':
                if 'box' not in submitted:
                    submitted.append('order')
                update = {'status': self.STATUS_FINISHED, 'steps.submitted': submitted}
                self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
                self.update_page_status(self.STATUS_FINISHED, self.task)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class PageCmpTxtApi(PageHandler):
    URL = '/api/page/cmp_txt/@page_name'

    def post(self, page_name):
        """ 根据OCR文本从CBETA库中查找相似文本作为比对本"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            ocr = self.get_txt(page, 'ocr')
            num = self.prop(self.data, 'num', 1)
            cmp, hit_page_codes = find_one(ocr, int(num))
            if cmp:
                self.send_data_response(dict(cmp=cmp, hit_page_codes=hit_page_codes))
            else:
                self.send_error_response(e.no_object, message='未找到比对文本')

        except self.DbError as error:
            return self.send_db_error(error)
        except ConnectionTimeout as error:
            return self.send_db_error(error)


class PageCmpTxtNeighborApi(PageHandler):
    URL = '/api/page/cmp_txt/neighbor'

    def post(self):
        """ 获取比对文本的前后页文本"""
        # param page_code: 当前cmp文本的page_code（对应于es库中的page_code）
        # param neighbor: prev/next，根据当前cmp文本的page_code往前或者往后找一条数据
        try:
            rules = [(v.not_empty, 'cmp_page_code', 'neighbor')]
            self.validate(self.data, rules)
            neighbor = find_neighbor(self.data.get('cmp_page_code'), self.data.get('neighbor'))
            if neighbor:
                txt = Diff.pre_cmp(''.join(neighbor['_source']['origin']))
                self.send_data_response(dict(txt=txt, code=neighbor['_source']['page_code']))
            else:
                self.send_data_response(dict(txt='', message='没有更多内容'))

        except self.DbError as error:
            return self.send_db_error(error)


class PageTxtDiffApi(PageHandler):
    URL = '/api/page/txt/diff'

    def post(self):
        """ 用户提交纯文本后重新比较，并设置修改痕迹"""
        try:
            rules = [(v.not_empty, 'texts')]
            self.validate(self.data, rules)
            diff_blocks = self.diff(*self.data['texts'])
            if self.data.get('hints'):
                diff_blocks = self.set_hints(diff_blocks, self.data['hints'])
            cmp_data = self.render_string('page_text_area.html', blocks=diff_blocks,
                                          sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))
            cmp_data = native_str(cmp_data)
            self.send_data_response(dict(cmp_data=cmp_data))

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def set_hints(diff_blocks, hints):
        for h in hints:
            line_segments = diff_blocks.get(h['block_no'], {}).get(h['line_no'])
            if not line_segments:
                continue
            for s in line_segments:
                if s['base'] == h['base'] and s['cmp1'] == h['cmp1']:
                    s['selected'] = True
        return diff_blocks


class PageDetectCharsApi(PageHandler):
    URL = '/api/page/txt/detect_chars'

    def post(self):
        """ 根据文本行内容识别宽字符"""
        try:
            mb4 = [[self.check_utf8mb4({}, t)['utf8mb4'] for t in s] for s in self.data['texts']]
            self.send_data_response(mb4)
        except Exception as error:
            return self.send_db_error(error)


class PageDeleteApi(BaseHandler):
    URL = '/api/page/delete'

    def post(self):
        """ 批量删除"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if self.data.get('_id'):
                r = self.db.page.delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_log('delete_page', target_id=self.data['_id'])
            else:
                r = self.db.page.delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_log('delete_page', target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class PageExportCharsApi(BaseHandler):
    URL = '/api/page/export_char'

    def post(self):
        """ 批量生成字表"""
        try:
            rules = [(v.not_empty, 'page_names')]
            self.validate(self.data, rules)
            # 启动脚本，生成字表
            script = 'nohup python3 %s/gen_chars.py --page_names="%s" --username="%s" >> log/gen_chars.log 2>&1 &'
            os.system(script % (path.dirname(__file__), ','.join(self.data['page_names']), self.username))
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class PageUpsertApi(PageHandler):
    URL = '/api/page'

    def post(self):
        """ 新增或修改 """
        try:
            r = Page.save_one(self.db, Page, self.data)
            if r.get('status') == 'success':
                self.add_log(('update_page' if r.get('update') else 'add_page'), context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except self.DbError as error:
            return self.send_db_error(error)


class PageSourceApi(BaseHandler):
    URL = '/api/page/source'

    def post(self):
        """ 更新分类"""
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db.page.update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_log('update_page', target_id=self.data['_id'])
            else:
                r = self.db.page.update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_log('update_page', target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class PageTaskPublishApi(PageHandler):
    URL = r'/api/page/task/publish'

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
            self.add_op_log(self.db, 'publish_task', log, self.username)
            return self.send_data_response(log)

        except self.DbError as error:
            return self.send_db_error(error)

    def get_page_names(self, log):
        """ 获取页码"""
        page_names = self.data.get('page_names')
        if page_names:
            if isinstance(page_names, str):
                self.data['page_names'] = page_names.split(',')
            return
        names_file = self.request.files.get('names_file')
        if names_file:
            names_str = str(names_file[0]['body'], encoding='utf-8').strip('\n')
            try:
                page_names = json.loads(names_str)
            except json.decoder.JSONDecodeError:
                ids_str = re.sub(r'\n+', '|', names_str)
                page_names = ids_str.split(r'|')
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
        # 去掉已发布和进行中的页码
        page_names, task_type, num = self.data['page_names'], self.data['task_type'], self.data.get('num')
        if page_names:
            status = [self.STATUS_PUBLISHED, self.STATUS_PENDING, self.STATUS_PICKED]
            cond = dict(task_type=task_type, num=num, status={'$in': status}, doc_id={'$in': list(page_names)})
            log['published_before'] = set(t['doc_id'] for t in self.db.task.find(cond, {'doc_id': 1}))
            page_names = set(page_names) - log['published_before']

        # 去掉已完成的页码（如果不重新发布）
        if not int(self.data['force']) and page_names:
            cond = dict(task_type=task_type, num=num, status=self.STATUS_FINISHED, doc_id={'$in': list(page_names)})
            log['finished_before'] = set(t['doc_id'] for t in self.db.task.find(cond, {'doc_id': 1}))
            page_names = set(page_names) - log['finished_before']

        # 剩下的页码，发布新任务
        if page_names:
            pre_tasks = self.data['pre_tasks']
            if pre_tasks:
                pre_tasks = [pre_tasks] if isinstance(pre_tasks, str) else pre_tasks
                db_pre_tasks = list(self.db.task.find(
                    {'collection': 'page', 'doc_id': {'$in': list(page_names)}, 'task_type': {'$in': pre_tasks}},
                    {'task_type': 1, 'num': 1, 'status': 1, 'doc_id': 1}
                ))
                # 前置任务未发布、未完成的情况，发布为PENDING
                un_published = set(page_names) - set(t['doc_id'] for t in db_pre_tasks)
                un_finished = set(t['doc_id'] for t in db_pre_tasks if t['status'] != self.STATUS_FINISHED)
                self.create_tasks(set(un_finished | un_published), self.STATUS_PENDING, {t: None for t in pre_tasks})
                log['pending'] = set(un_finished | un_published)
                # 前置任务未完成的情况，发布为PENDING
                page_names = set(page_names) - log['pending']
                if page_names:
                    self.create_tasks(page_names, self.STATUS_PUBLISHED, {t: self.STATUS_FINISHED for t in pre_tasks})
                    log['published'] = page_names
            else:
                self.create_tasks(page_names, self.STATUS_PUBLISHED)
                log['published'] = page_names

        return {k: v for k, v in log.items() if v}

    def create_tasks(self, page_names, status, pre_tasks=None):
        def get_task(page_name):
            steps = self.data.get('steps') and dict(todo=self.data['steps'])
            return dict(task_type=self.data['task_type'], num=self.data.get('num'), batch=self.data['batch'],
                        collection='page', id_name='name', doc_id=page_name, status=status, steps=steps,
                        priority=self.data['priority'], pre_tasks=pre_tasks, params=None, result={},
                        create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                        publish_user_id=self.user_id, publish_by=self.username)

        if page_names:
            self.db.task.insert_many([get_task(name) for name in page_names], ordered=False)
            num = '_' + str(self.data['num']) if self.data.get('num') else ''
            update = {'tasks.' + self.data['task_type'] + num: self.STATUS_PUBLISHED}
            self.db.page.update_many({'name': {'$in': list(page_names)}}, {'$set': update})
