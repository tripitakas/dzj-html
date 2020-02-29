#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from bson.objectid import ObjectId
from tornado.escape import to_basestring
from .page import Page
from controller import errors as e
from controller import validate as v
from controller.task.task import Task
from controller.base import BaseHandler
from controller.helper import name2code

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class PageAdminHandler(BaseHandler, Page):
    URL = '/data/page'

    # 列表相关参数
    page_title = '页数据管理'
    search_tips = '请搜索页编码、分类、页面结构、统一经编码、卷编码'
    search_fields = ['name', 'source', 'layout', 'uni_sutra_code', 'reel_code']
    table_fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'img_cloud_path', 'name': '云图路径'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'level-box', 'name': '切分等级'},
        {'id': 'level-text', 'name': '文本等级'},
        {'id': 'lock-box', 'name': '切分锁'},
        {'id': 'lock-text', 'name': '文本锁'},
        {'id': 'remark-box', 'name': '切分备注'},
        {'id': 'remark-text', 'name': '文字备注'},
    ]
    info_fields = [
        'name', 'source', 'box_ready', 'layout', 'level-box', 'level-text',
        'remark-box', 'remark-text'
    ]
    hide_fields = [
        'img_cloud_path', 'uni_sutra_code', 'sutra_code', 'reel_code', 'box_ready',
        'lock-box', 'lock-text', 'level-box', 'level-text'
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-export-char', 'label': '生成字表'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in Task.get_task_types('page').items()
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-box', 'label': '字框'},
        {'action': 'btn-order', 'label': '字序'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    update_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'source', 'name': '分类'},
        {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': Page.layouts},
        {'id': 'level-box', 'name': '切分等级'},
        {'id': 'level-text', 'name': '文本等级'},
        {'id': 'remark-box', 'name': '切分备注'},
        {'id': 'remark-text', 'name': '文本备注'},
    ]
    task_statuses = {
        '': '', 'un_published': '未发布', 'published': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }

    def get_duplicate_condition(self):
        pages = list(self.db.page.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'name': {'$in': [p['_id'] for p in pages]}}
        params = {'duplicate': 'true'}
        return condition, params

    def get(self):
        """ 页数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']

            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = self.get_page_search_condition(self.request.query)
            fields = ['chars', 'columns', 'blocks', 'ocr', 'ocr_col', 'text', 'txt_html', 'char_ocr']
            docs, pager, q, order = self.find_by_page(self, condition, None, 'page_code', {f: 0 for f in fields})

            self.render('page_admin.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, format_value=self.format_value,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageViewHandler(BaseHandler, Page):
    URL = '/page/@page_name'

    edit_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': Page.layouts},
        {'id': 'source', 'name': '分　　类'},
        {'id': 'level-box', 'name': '切分等级'},
        {'id': 'level-text', 'name': '文本等级'},
    ]

    def get(self, page_name):
        """ 浏览页面数据"""

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            condition = self.get_page_search_condition(self.request.query)[0]
            to = self.get_query_argument('to', '')
            if to == 'next':
                condition['page_code'] = {'$gt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', 1)])
            elif to == 'prev':
                condition['page_code'] = {'$lt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', -1)])
            if not page:
                message = '没有找到页面%s的%s' % (page_name, '上一页' if to == 'prev' else '下一页')
                return self.send_error_response(e.no_object, message=message)

            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            btn_config = json_util.loads(self.get_secure_cookie('data_page_button') or '{}')
            info = {f['id']: self.prop(page, f['id'].replace('-', '.'), '') for f in self.edit_fields}
            labels = dict(text='审定文本', ocr='字框OCR', ocr_col='列框OCR')
            texts = [(f, page.get(f), labels.get(f)) for f in ['ocr', 'ocr_col', 'text'] if page.get(f)]
            self.render('page_view.html', page=page, chars_col=chars_col, btn_config=btn_config,
                        texts=texts, Task=Task, info=info, edit_fields=self.edit_fields,
                        img_url=img_url)

        except Exception as error:
            return self.send_db_error(error)


class PageInfoHandler(BaseHandler, Page):
    URL = '/page/info/@page_name'

    def get(self, page_name):
        """ 页面详情"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            fields1 = ['lock.box', 'lock.text', 'level.box', 'level.text']
            data_lock = {k: self.prop(page, k) for k in fields1 if self.prop(page, k)}
            fields2 = ['ocr', 'ocr_col', 'text']
            page_txt = {k: self.prop(page, k) for k in fields2 if self.prop(page, k)}
            fields3 = ['blocks', 'columns', 'chars', 'chars_col']
            page_box = {k: self.prop(page, k) for k in fields3 if self.prop(page, k)}
            fields4 = list(set(page.keys()) - set(fields1 + fields2 + fields3))
            metadata = {k: self.prop(page, k) for k in fields4 if self.prop(page, k)}
            page_tasks = self.prop(page, 'tasks') or {}

            self.render('page_info.html', metadata=metadata, data_lock=data_lock, page_txt=page_txt,
                        page_box=page_box, page_tasks=page_tasks, page=page, Task=Task)

        except Exception as error:
            return self.send_db_error(error)


class PageUploadApi(BaseHandler, Page):
    URL = '/api/data/page/upload'

    def post(self):
        """ 批量上传 """
        upload_file = self.request.files.get('csv') or self.request.files.get('json')
        content = to_basestring(upload_file[0]['body'])
        with StringIO(content) as fn:
            assert self.data.get('layout'), 'need layout'
            r = self.insert_many(self.db, file_stream=fn, layout=self.data['layout'])
            if r.get('status') == 'success':
                self.send_data_response(r)
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class PageUpdateSourceApi(BaseHandler, Page):
    URL = '/api/page/source'

    def post(self):
        """ 批量更新分类"""
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db.page.update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_op_log('update_page', target_id=self.data['_id'])
            else:
                r = self.db.page.update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_op_log('update_page', target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class PageExportCharApi(BaseHandler, Page):
    URL = '/api/page/export_char'

    def post(self):
        """ 批量生成字表"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            chars = []
            invalid_pages = []
            invalid_chars = []
            project = {'name': 1, 'chars': 1, 'columns': 1, 'source': 1}
            _ids = [self.data['_id']] if self.data.get('_id') else self.data['_ids']
            pages = self.db.page.find({'_id': {'$in': [ObjectId(i) for i in _ids]}}, project)
            for p in pages:
                self.export_chars(p, chars, invalid_chars, invalid_pages)
            # 插入数据库，忽略错误
            r = self.db.char.insert_many(chars, ordered=False)
            inserted_chars = [c['_id'] for c in list(self.db.char.find({'_id': {'$in': r.inserted_ids}}))]
            # 未插入的数据，进行更新
            un_inserted_chars = [c for c in chars if c['_id'] not in inserted_chars]
            for c in un_inserted_chars:
                self.db.char.update_one({'_id': c['_id']}, {'$set': {'pos': c['pos']}})

            self.send_data_response(inserted_count=len(chars), invalid_pages=invalid_pages, invalid_chars=invalid_chars)

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def export_chars(p, chars, invalid_chars, invalid_pages):
        try:
            col2cid = {cl['column_id']: cl['cid'] for cl in p['columns']}
            for c in p.get('chars', []):
                try:
                    txt = c.get('txt') or c.get('ocr_txt')
                    char_name = '%s_%s' % (p['name'], c['cid'])
                    pos = dict(x=c['x'], y=c['y'], w=c['w'], h=c['h'])
                    column_cid = col2cid.get('b%sc%s' % (c['block_no'], c['column_no']))
                    c = {'page_name': p['name'], 'cid': c['cid'], 'name': char_name, 'column_cid': column_cid,
                         'char_code': name2code(char_name), 'source': p.get('source'),
                         'ocr': c['ocr_txt'], 'txt': txt, 'cc': c.get('cc'),
                         'sc': c.get('sc'), 'pos': pos}
                    chars.append(c)
                except KeyError:
                    invalid_chars.append(c)
        except KeyError:
            invalid_pages.append(p)
