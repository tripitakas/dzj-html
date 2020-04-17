#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os import path
from bson.objectid import ObjectId
from tornado.escape import native_str
from elasticsearch.exceptions import ConnectionTimeout
from .tool.diff import Diff
from .page import Page
from .base import PageHandler
from .publish import PublishHandler
from .tool.esearch import find_one, find_neighbor
from controller import errors as e
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


class PageTaskPublishApi(PublishHandler):
    URL = r'/api/page/task/publish'

    def post(self):
        """ 发布任务"""
        self.data['doc_ids'] = self.get_doc_ids(self.data)
        rules = [
            (v.not_empty, 'doc_ids', 'task_type', 'priority', 'force', 'batch'),
            (v.in_list, 'task_type', list(self.task_types.keys())),
            (v.in_list, 'pre_tasks', list(self.task_types.keys())),
            (v.is_priority, 'priority'),
        ]
        self.validate(self.data, rules)

        try:
            if len(self.data['doc_ids']) > self.MAX_PUBLISH_RECORDS:
                message = '任务数量不能超过%s' % self.MAX_PUBLISH_RECORDS
                return self.send_error_response(e.task_count_exceed, message=message)
            log = self.publish_many(
                self.data['task_type'], self.data.get('pre_tasks', []), self.data.get('steps', []),
                self.data['priority'], self.data['force'] == '是',
                self.data['doc_ids'], self.data['batch']
            )
            return self.send_data_response({k: value for k, value in log.items() if value})

        except self.DbError as error:
            return self.send_db_error(error)

    def get_doc_ids(self, data):
        """ 获取页码，有四种方式：页编码、文件、前缀、检索参数"""
        doc_ids = data.get('doc_ids') or []
        if doc_ids:
            return doc_ids
        ids_file = self.request.files.get('ids_file')
        collection, id_name, input_field = self.get_data_conf(data['task_type'])[:3]
        if ids_file:
            ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
            try:
                doc_ids = json.loads(ids_str)
            except json.decoder.JSONDecodeError:
                ids_str = re.sub(r'\n+', '|', ids_str)
                doc_ids = ids_str.split(r'|')
        elif data.get('prefix'):
            condition = {id_name: {'$regex': data['prefix'], '$options': '$i'}}
            if input_field:
                condition[input_field] = {"$nin": [None, '']}
            doc_ids = [doc.get(id_name) for doc in self.db[collection].find(condition)]
        elif data.get('search'):
            condition = Page.get_page_search_condition(data['search'])[0]
            query = self.db[collection].find(condition)
            page = h.get_url_param('page', data['search'])
            if page:
                size = h.get_url_param('page_size', data['search']) or self.prop(self.config, 'pager.page_size', 10)
                query = query.skip((int(page) - 1) * int(size)).limit(int(size))
            doc_ids = [doc.get(id_name) for doc in list(query)]
        return doc_ids


class PageTaskMyHandler(PageHandler):
    URL = '/task/my/@page_task'

    search_tips = '请搜索页编码'
    search_fields = ['doc_id']
    operations = []
    img_operations = []
    actions = [
        {'action': 'my-task-view', 'label': '查看'},
        {'action': 'my-task-do', 'label': '继续', 'disabled': lambda d: d['status'] == 'finished'},
        {'action': 'my-task-update', 'label': '更新', 'disabled': lambda d: d['status'] == 'picked'},
    ]
    table_fields = [
        {'id': 'doc_id', 'name': '页编码'},
        {'id': 'task_type', 'name': '类型'},
        {'id': 'status', 'name': '状态'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['task_type']
    info_fields = ['doc_id', 'task_type', 'status', 'picked_time', 'finished_time']
    update_fields = []

    def get(self, task_type):
        """ 我的任务"""
        try:
            condition = {
                'task_type': {'$regex': task_type} if self.is_group(task_type) else task_type,
                'status': {'$in': [self.STATUS_PICKED, self.STATUS_FINISHED]},
                'picked_user_id': self.user_id
            }
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-picked_time')
            kwargs = self.get_template_kwargs()
            self.render('task_my.html', docs=docs, pager=pager, q=q, order=order,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
