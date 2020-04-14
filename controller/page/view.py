#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from tornado.web import UIModule
from tornado.escape import to_basestring
from .model import Page, Char
from .base import PageHandler
from controller import errors as e
from controller.base import BaseHandler
from controller.task.task import Task
from controller.task.base import TaskHandler


class PageViewHandler(PageHandler):
    URL = '/page/@page_name'

    def get(self, page_name):
        """ 查看Page页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            self.pack_boxes(page)
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            txt_off = self.get_query_argument('txt', None) == 'off'
            cid = self.get_query_argument('char_name', '').split('_')[-1]
            texts = [(self.get_txt(page, f), f, Page.get_field_name(f)) for f in ['text', 'ocr', 'ocr_col', 'cmp']]
            texts = [t for t in texts if t[0]]
            self.render('page_view.html', texts=texts, img_url=img_url, page=page, chars_col=chars_col,
                        txt_off=txt_off, cur_cid=cid)

        except Exception as error:
            return self.send_db_error(error)


class BoxHandler(PageHandler):
    URL = ['/page/box/@page_name',
           '/page/box/edit/@page_name']

    def get(self, page_name):
        """ 切分校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            self.check_box_access(page, 'raw')
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_box.html', page=page, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class OrderHandler(PageHandler):
    URL = ['/page/order/@page_name',
           '/page/order/edit/@page_name']

    def get(self, page_name):
        """ 字序校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            reorder = self.get_query_argument('reorder', '')
            if reorder:
                page['chars'] = self.reorder_boxes(page=page, direction=reorder)[2]
            chars_col = self.get_chars_col(page['chars'])
            self.render('page_order.html', page=page, chars_col=chars_col, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class CmpTxtHandler(PageHandler):
    URL = ['/page/cmp_txt/@page_name',
           '/page/cmp_txt/edit/@page_name']

    def get(self, page_name):
        """ 比对文本页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            ocr = self.get_txt(page, 'ocr')
            cmp = self.get_txt(page, 'cmp')
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_cmp_txt.html', page=page, ocr=ocr, cmp=cmp, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class TxtHandler(PageHandler):
    URL = ['/page/txt/@page_name',
           '/page/txt/edit/@page_name']

    def get(self, page_name):
        """ 文字校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            txts = [(self.get_txt(page, f), f, Page.get_field_name(f)) for f in ['txt', 'ocr', 'ocr_col', 'cmp']]
            txts = [t for t in txts if t[0]]
            txt_dict = {t[1]: t for t in txts}
            cmp_data = self.prop(page, 'txt_html')
            txt_fields = self.prop(page, 'txt_fields')
            doubts = [(self.prop(page, 'txt_doubt', ''), '校对存疑')]
            if not cmp_data:
                txt_fields = [t[1] for t in txts]
                cmp_data = self.diff(*[t[0] for t in txts])
                cmp_data = to_basestring(TextArea(self).render(cmp_data))
            readonly = '/edit' not in self.request.path
            img_url = self.get_web_img(page['name'], 'page')
            return self.render('page_txt.html', page=page, img_url=img_url, txts=txts, txt_dict=txt_dict,
                               txt_fields=txt_fields, cmp_data=cmp_data,
                               doubts=doubts, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class TaskCutHandler(PageHandler):
    URL = ['/task/@cut_task/@task_id',
           '/task/do/@cut_task/@task_id',
           '/task/browse/@cut_task/@task_id',
           '/task/update/@cut_task/@task_id']

    def get(self, task_type, task_id):
        """ 切分校对、审定任务页面"""
        try:
            page = self.db.page.find_one({'name': self.task['doc_id']})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % self.task['doc_id'])
            self.pack_boxes(page)
            img_url = self.get_web_img(page['name'], 'page')
            if self.steps['current'] == 'order':
                reorder = self.get_query_argument('reorder', '')
                if reorder:
                    page['chars'] = self.reorder_boxes(page=page, direction=reorder)[2]
                chars_col = self.get_chars_col(page['chars'])
                self.render('page_order.html', page=page, img_url=img_url, readonly=self.readonly,
                            chars_col=chars_col)
            else:
                kwargs = dict(input_type='radio', options=['是', '否'], default='是')
                config_fields = [
                    dict(id='auto-pick', name='提交后自动领新任务', **kwargs),
                    dict(id='auto-adjust', name='自适应调整栏框和列框', **kwargs),
                    dict(id='detect-col', name='自适应调整字框在多列的情况', **kwargs),
                ]
                self.render('page_box.html', page=page, img_url=img_url, readonly=self.readonly,
                            config_fields=config_fields)

        except Exception as error:
            return self.send_db_error(error)


class CutEditHandler(PageHandler):
    URL = ['/page/cut_edit/@page_name',
           '/page/cut_view/@page_name']

    def get(self, page_name):
        """ 切分编辑页面"""
        kwargs = dict(input_type='radio', options=['是', '否'], default='是')
        config_fields = [
            dict(id='auto-adjust', name='自适应调整栏框和列框', **kwargs),
            dict(id='detect-col', name='自适应调整字框在多列的情况', **kwargs),
        ]

        try:
            template = 'page_task_cut.html'
            if self.steps['current'] == 'order':
                template = 'page_task_order.html'
                reorder = self.get_query_argument('reorder', '')
                if reorder:
                    boxes = self.reorder_boxes(page=self.page, direction=reorder)
                    self.page['blocks'], self.page['columns'], self.page['chars'] = boxes
                self.chars_col = self.get_chars_col(self.page['chars'])
            self.render(template, page=self.page, img_url=self.get_page_img(self.page),
                        config_fields=config_fields, chars_col=self.chars_col)

        except Exception as error:
            return self.send_db_error(error)


class TaskTextProofHandler(PageHandler):
    URL = ['/task/text_proof_@num/@task_id',
           '/task/do/text_proof_@num/@task_id',
           '/task/browse/text_proof_@num/@task_id',
           '/task/update/text_proof_@num/@task_id']

    def get(self, num, task_id):
        """ 文字校对页面"""
        try:
            img_url = self.get_page_img(self.page)
            if not self.get_query_argument('step', '') and self.steps['current'] == 'select' and self.page.get('cmp'):
                self.steps.update(dict(current='proof', is_first=False, is_last=True, prev='select', next=None))

            if self.steps['current'] == 'select':
                return self.render('page_task_select.html', page=self.page, img_url=img_url,
                                   ocr=self.get_txt('ocr'), cmp=self.get_txt('cmp'))
            else:
                texts, doubts = self.get_cmp_data()
                text_dict = {t[1]: t for t in texts}
                cmp_data = self.prop(self.task, 'result.txt_html')
                text_fields = self.prop(self.task, 'result.text_fields')
                if not cmp_data:
                    text_fields = [t[1] for t in texts]
                    cmp_data = self.diff(*[t[0] for t in texts])
                    cmp_data = to_basestring(TextArea(self).render(cmp_data))
                return self.render('page_task_text.html', page=self.page, img_url=img_url, texts=texts,
                                   text_dict=text_dict, doubts=doubts, cmp_data=cmp_data,
                                   text_fields=text_fields or list(text_dict.keys()))

        except Exception as error:
            return self.send_db_error(error)


class TaskTextReviewHandler(PageHandler):
    URL = ['/task/(text_review|text_hard)/@task_id',
           '/task/do/(text_review|text_hard)/@task_id',
           '/task/browse/(text_review|text_hard)/@task_id',
           '/task/update/(text_review|text_hard)/@task_id']

    def get(self, task_type, task_id):
        """ 文字审定、难字处理页面"""
        try:
            self.texts, self.doubts = self.get_cmp_data()
            cmp_data = self.prop(self.page, 'txt_html')
            if not cmp_data and len(self.texts):
                cmp_data = self.diff(*[t[0] for t in self.texts])
            self.render('page_task_text.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class TextEditHandler(PageHandler):
    URL = ['/page/text_edit/@page_name',
           '/page/text_view/@page_name']

    def get(self, page_name):
        """ 文字查看、修改页面"""
        try:
            self.texts, self.doubts = self.get_cmp_data()
            cmp_data, text = self.page.get('txt_html') or '', self.page.get('text') or ''
            if not cmp_data and not text:
                self.send_error_response(e.no_object, message='没有找到审定文本')

            if not cmp_data and text:
                cmp_data = self.diff(text)
                cmp_data = to_basestring(TextArea(self).render(cmp_data))

            self.render('page_task_text.html', cmp_data=cmp_data)

        except Exception as error:
            return self.send_db_error(error)


class CharEditHandler(PageHandler):
    URL = ['/page/char_edit/@page_name']

    def get(self, page_name):
        """ 单字修改页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            chars = page['chars']
            chars_col = self.get_chars_col(chars)
            char_dict = {c['cid']: c for c in chars}
            img_url = self.get_web_img(page['name'])
            txt_types = {'': '没问题', 'M': '模糊或残损', 'N': '不确定', '*': '不认识'}
            self.render('page_char_edit.html', img_url=img_url, page=page, chars=chars, chars_col=chars_col,
                        char_dict=char_dict, txt_types=txt_types)

        except Exception as error:
            return self.send_db_error(error)


class PageBrowseHandler(PageHandler):
    URL = '/page/browse/@page_name'

    def get(self, page_name):
        """ 浏览页面数据"""

        edit_fields = [
            {'id': 'name', 'name': '页编码', 'readonly': True},
            {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
            {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': self.layouts},
            {'id': 'source', 'name': '分　　类'},
            {'id': 'level-box', 'name': '切分等级'},
            {'id': 'level-text', 'name': '文本等级'},
        ]
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
            info = {f['id']: self.prop(page, f['id'].replace('-', '.'), '') for f in edit_fields}
            labels = dict(text='审定文本', ocr='字框OCR', ocr_col='列框OCR')
            texts = [(page.get(f), f, labels.get(f)) for f in ['ocr', 'ocr_col', 'text'] if page.get(f)]
            self.render('page_browse.html', page=page, chars_col=chars_col, btn_config=btn_config,
                        texts=texts, info=info, edit_fields=edit_fields, img_url=img_url)

        except Exception as error:
            return self.send_db_error(error)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, cmp_data):
        return self.render_string('page_text_area.html', blocks=cmp_data,
                                  sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))


class PageListHandler(BaseHandler, Page):
    URL = '/data/page'

    # 列表相关参数
    page_title = '页数据管理'
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
        {'action': 'btn-cmp-txt', 'label': '比对文本'},
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
            fields = ['chars', 'columns', 'blocks', 'ocr', 'ocr_col', 'text', 'txt_html']
            docs, pager, q, order = self.find_by_page(self, condition, None, 'page_code', {f: 0 for f in fields})

            self.render('data_page_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, format_value=self.format_value,
                        Task=Task, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageInfoHandler(BaseHandler, Page):
    URL = '/data/page/info/@page_name'

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

            self.render('data_page_info.html', metadata=metadata, data_lock=data_lock, page_txt=page_txt,
                        page_box=page_box, page_tasks=page_tasks, page=page, Task=Task)

        except Exception as error:
            return self.send_db_error(error)


class CharListHandler(BaseHandler, Char):
    URL = '/data/char'

    page_title = '字数据管理'
    table_fields = [
        {'id': 'has_img', 'name': '字图'},
        {'id': 'source', 'name': '分类'},
        {'id': 'page_name', 'name': '页编码'},
        {'id': 'cid', 'name': 'cid'},
        {'id': 'name', 'name': '字编码'},
        {'id': 'char_id', 'name': '字序'},
        {'id': 'uid', 'name': '字序id'},
        {'id': 'data_level', 'name': '数据等级'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'column', 'name': '所属列'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'txt', 'name': '正字'},
        {'id': 'ori_txt', 'name': '原字'},
        {'id': 'ocr_txt', 'name': '字框OCR'},
        {'id': 'col_txt', 'name': '列框OCR'},
        {'id': 'cmp_txt', 'name': '比对文字'},
        {'id': 'alternatives', 'name': 'OCR候选'},
        {'id': 'txt_logs', 'name': '校对记录'},
        {'id': 'proof_count', 'name': '校对次数'},
        {'id': 'review_count', 'name': '审定次数'},
        {'id': 'remark', 'name': '备注'},
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-gen-img', 'label': '生成字图'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-browse', 'label': '浏览结果'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'source', 'label': '按分类'},
            {'operation': 'txt', 'label': '按正字'},
            {'operation': 'ocr_txt', 'label': '按OCR'},
            {'operation': 'ori_txt', 'label': '按原字'},
        ]},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in Task.get_task_types('char').items()
        ]},
    ]
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    hide_fields = ['page_name', 'cid', 'uid', 'data_level', 'txt_logs', 'sc', 'pos', 'column', 'proof_count']
    info_fields = ['has_img', 'source', 'txt', 'ori_txt', 'txt_type', 'remark']
    update_fields = [
        {'id': 'txt_type', 'name': '类型', 'input_type': 'radio', 'options': Char.txt_types},
        {'id': 'source', 'name': '分类'},
        {'id': 'txt', 'name': '正字'},
        {'id': 'ori_txt', 'name': '原字'},
        {'id': 'remark', 'name': '备注'},
    ]

    def get_duplicate_condition(self):
        chars = list(self.db.char.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'id': {'$in': [c['_id'] for c in chars]}}
        params = {'duplicate': 'true'}
        return condition, params

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""
        if key == 'pos':
            return '/'.join([str(value.get(f)) for f in ['x', 'y', 'w', 'h']])
        if key == 'txt_type':
            return self.txt_types.get(value, value)
        if key in ['cc', 'sc'] and value:
            return value / 1000
        if key == 'has_img' and value not in [None, False]:
            return r'<img class="char-img" src="%s"/>' % self.get_web_img(doc['name'], 'char')
        return h.format_value(value, key, doc)

    def get(self):
        """ 字数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = self.get_char_search_condition(self.request.query)
            docs, pager, q, order = self.find_by_page(self, condition)
            self.render('data_char_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        Task=Task, txt_types=self.txt_types, format_value=self.format_value,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CharStatisticHandler(BaseHandler, Char):
    URL = '/data/char/statistic'

    def get(self):
        """ 统计字数据"""
        try:
            condition = self.get_char_search_condition(self.request.query)[0]
            kind = self.get_query_argument('kind', '')
            if kind not in ['source', 'txt', 'ocr_txt', 'ori_txt']:
                return self.send_error_response(e.statistic_type_error, message='只能按分类、原字、正字和OCR文字统计')
            aggregates = [{'$group': {'_id': '$' + kind, 'count': {'$sum': 1}}}]
            docs, pager, q, order = self.aggregate_by_page(self, condition, aggregates, default_order='-count')
            self.render('char_statistic.html', docs=docs, pager=pager, q=q, order=order, kind=kind)

        except Exception as error:
            return self.send_db_error(error)
