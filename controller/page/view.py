#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import math
from bson import json_util
from controller import errors as e
from controller import helper as h
from controller.task.task import Task
from controller.page.page import Page
from controller.page.base import PageHandler
from controller.char.base import CharHandler


class PageListHandler(PageHandler):
    URL = '/page/list'

    page_title = '页数据管理'
    table_fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_txt', 'name': '文本备注'},
        {'id': 'op_text', 'name': '文本匹配'},
    ]
    info_fields = [
        'name', 'source', 'box_ready', 'layout', 'remark_box', 'op_text'
    ]
    hide_fields = [
        'uni_sutra_code', 'sutra_code', 'reel_code', 'box_ready', 'box_ready',
    ]
    actions = [
        {'action': 'btn-box', 'label': '字框'},
        {'action': 'btn-order', 'label': '字序'},
        {'action': 'btn-text', 'label': '文字'},
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-my-view', 'label': '查看'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-delete', 'label': '删除'},
    ]
    update_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'source', 'name': '分　类'},
        {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': PageHandler.layouts},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_txt', 'name': '文本备注'},
    ]
    task_statuses = {
        '': '', 'un_published': '未发布', 'published': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }
    match_fields = {'cmp_txt': '比对文本', 'ocr_col': 'OCR列文', 'txt': '校对文本'}
    match_statuses = {'': '', None: '无', True: '匹配', False: '不匹配'}

    def get_operations(self):
        operations = [
            {'operation': 'bat-delete', 'label': '批量删除'},
            {'operation': 'btn-duplicate', 'label': '查找重复'},
            {'operation': 'bat-source', 'label': '更新分类'},
            {'operation': 'bat-gen-chars', 'label': '生成字表'},
            {'operation': 'btn-check-match', 'label': '检查图文匹配'},
            {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
            {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
                {'operation': k, 'label': name} for k, name in PageHandler.task_names('page', True, False).items()
            ]},
        ]
        if self.prop(self.config, 'site.skin') == 'nlc':
            operations = [o for o in operations if o.get('label') not in ['生成字表', '检查图文匹配']]
        if '系统管理员' in self.current_user['roles']:
            operations[-1]['groups'] = [
                {'operation': k, 'label': name} for k, name in PageHandler.task_names('page', True, True).items()
            ]
        return operations

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""

        def format_txt(field, show_none=True):
            txt = self.get_txt(doc, field)
            st = {True: '√', False: '×'}.get(self.prop(doc, 'txt_match.%s.status' % field)) or ''
            if txt:
                return '<a title="%s">%s%s</a>' % (field, self.match_fields.get(field), st)
            elif show_none:
                return '<a title="%s">%s%s(无)</a>' % (field, self.match_fields.get(field), st)
            else:
                return ''

        if key == 'tasks' and value:
            ret = ''
            for tsk_type, tasks in value.items():
                if isinstance(tasks, dict):
                    for num, status in tasks.items():
                        ret += '%s#%s/%s<br/>' % (self.get_task_name(tsk_type), num, self.get_status_name(status))
                else:
                    ret += '%s/%s<br/>' % (self.get_task_name(tsk_type), self.get_status_name(tasks))
            return ret.rstrip('<br/>')
        if key == 'op_text':
            return '<br/>'.join([format_txt(k, k != 'txt') for k in ['ocr_col', 'cmp_txt', 'txt']])
        return h.format_value(value, key, doc)

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
            kwargs['operations'] = self.get_operations()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']

            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = Page.get_page_search_condition(self.request.query)
            # fields = ['chars', 'columns', 'blocks', 'cmp_txt', 'ocr', 'ocr_col', 'txt']
            docs, pager, q, order = Page.find_by_page(self, condition, default_order='name')
            self.render('page_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, match_statuses=self.match_statuses,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageBrowseHandler(PageHandler):
    URL = '/page/browse/@page_name'

    def get(self, page_name):
        """ 浏览页面数据"""
        edit_fields = [
            {'id': 'name', 'name': '页编码', 'readonly': True},
            {'id': 'source', 'name': '分　类'},
            {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': self.layouts},
            {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
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

            txts = self.get_txts(page)
            txt_fields = [t[1] for t in txts]
            txt_dict = {t[1]: t for t in txts}
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            info = {f['id']: self.prop(page, f['id'], '') for f in edit_fields}
            btn_config = json_util.loads(self.get_secure_cookie('page_browse_btn') or '{}')
            active = btn_config.get('sutra-txt')
            self.pack_boxes(page)
            self.render(
                'page_browse.html', page=page, img_url=img_url, txts=txts, txt_dict=txt_dict,
                active=active, txt_fields=txt_fields, chars_col=chars_col, info=info,
                btn_config=btn_config, edit_fields=edit_fields,
            )

        except Exception as error:
            return self.send_db_error(error)


class PageViewHandler(PageHandler):
    URL = '/page/@page_name'

    def get(self, page_name):
        """ 查看Page页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            txts = self.get_txts(page)
            txt_fields = [t[1] for t in txts]
            txt_dict = {t[1]: t for t in txts}
            cid = self.get_query_argument('cid', '')
            img_url = self.get_web_img(page['name'])
            chars_col = self.get_chars_col(page['chars'])
            txt_off = self.get_query_argument('txt', None) == 'off'
            self.pack_boxes(page)
            self.render(
                'page_view.html', page=page, img_url=img_url, txts=txts, txt_dict=txt_dict,
                active=None, txt_fields=txt_fields, txt_off=txt_off, chars_col=chars_col,
                cur_cid=cid,
            )

        except Exception as error:
            return self.send_db_error(error)


class PageInfoHandler(PageHandler):
    URL = '/page/info/@page_name'

    def format_value(self, value, key=None, doc=None):
        """ 格式化task表的字段输出"""
        if key in ['blocks', 'columns', 'chars'] and value:
            return '<div>%s</div>' % '</div><div>'.join([str(v) for v in value])
        return h.format_value(value, key, doc)

    def get(self, page_name):
        """ 页面详情"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            page_tasks = self.prop(page, 'tasks') or {}
            fields1 = ['txt', 'ocr', 'ocr_col', 'cmp_txt']
            page_txts = {k: self.get_txt(page, k) for k in fields1 if self.get_txt(page, k)}
            fields2 = ['blocks', 'columns', 'chars', 'chars_col']
            page_boxes = {k: self.prop(page, k) for k in fields2 if self.prop(page, k)}
            fields3 = list(set(page.keys()) - set(fields1 + fields2) - {'bak', 'tasks', 'txt_match'})
            metadata = {k: self.prop(page, k) for k in fields3 if self.prop(page, k)}

            self.render('page_info.html', page=page, metadata=metadata, page_txts=page_txts, page_boxes=page_boxes,
                        page_tasks=page_tasks, Page=Page, Task=Task, format_value=self.format_value)

        except Exception as error:
            return self.send_db_error(error)


class PageBoxHandler(PageHandler):
    URL = '/page/box/@page_name'

    def get(self, page_name):
        """ 切分校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.set_box_access(page)
            sub_columns = self.get_query_argument('sub_columns', '')
            self.pack_boxes(page, sub_columns == 'true')
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_box.html', page=page, img_url=img_url, readonly=False)

        except Exception as error:
            return self.send_db_error(error)


class PageOrderHandler(PageHandler):
    URL = '/page/order/@page_name'

    def get(self, page_name):
        """ 字序校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            img_url = self.get_web_img(page['name'], 'page')
            reorder = self.get_query_argument('reorder', '')
            if reorder:
                page['chars'] = self.reorder_boxes(page=page, direction=reorder)[2]
            chars_col = self.get_chars_col(page['chars'])
            self.pack_boxes(page)
            self.render('page_order.html', page=page, chars_col=chars_col, img_url=img_url, readonly=False)

        except Exception as error:
            return self.send_db_error(error)


class PageTxtMatchHandler(PageHandler):
    URL = '/page/txt_match/@page_name'

    def get(self, page_name):
        """ 文字匹配页面"""
        field = self.get_query_argument('field', '')
        assert field in ['txt', 'cmp_txt', 'ocr_col']
        self.txt_match(self, field, page_name)

    @staticmethod
    def txt_match(self, field, page_name):
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            cmp_txt = self.prop(page, 'txt_match.%s.value' % field) or self.get_txt(page, field)
            field_name = Page.get_field_name(field)
            if not cmp_txt:
                if field == 'cmp_txt':
                    self.redirect('/page/find_cmp/' + page_name)
                else:
                    self.send_error_response(e.no_object, message='页面没有%s' % field_name)

            char_txt = self.get_txt(page, 'ocr')
            txts = [(cmp_txt, field, field_name), (char_txt, 'ocr', '字框OCR')]
            txt_dict = {t[1]: t for t in txts}
            cmp_data = self.match_diff(char_txt, cmp_txt)
            img_url = self.get_web_img(page['name'], 'page')
            txt_match = self.prop(page, 'txt_match.' + field)
            self.pack_boxes(page)
            self.render(
                'page_match.html', page=page, img_url=img_url, char_txt=char_txt, cmp_data=cmp_data,
                field=field, field_name=field_name, txt_match=txt_match, txts=txts,
                txt_fields=[field, 'OCR'], txt_dict=txt_dict, active='work-html',
            )

        except Exception as error:
            return self.send_db_error(error)


class PageFindCmpHandler(PageHandler):
    URL = '/page/find_cmp/@page_name'

    def get(self, page_name):
        """ 寻找比对文本页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_boxes(page)
            img_url = self.get_web_img(page['name'], 'page')
            self.render('page_find_cmp.html', page=page, img_url=img_url, readonly=True, ocr=self.get_txt(page, 'ocr'),
                        cmp_txt=self.get_txt(page, 'cmp_txt'), )

        except Exception as error:
            return self.send_db_error(error)


class PageTxtHandler(PageHandler):
    URL = '/page/txt/@page_name'

    def get(self, page_name):
        """ 单字修改页面"""
        try:
            self.page_title = '文字校对'
            self.page_txt(self, page_name)

        except Exception as error:
            return self.send_db_error(error)

    @staticmethod
    def page_txt(self, page_name):
        page = self.db.page.find_one({'name': page_name})
        if not page:
            self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

        # 设置字框大小
        ch_a = sorted([c['w'] * c['h'] for c in page['chars']])
        ch_a = ch_a[:-2] if len(ch_a) > 4 else ch_a[:-1] if len(ch_a) > 3 else ch_a
        ch_a = ch_a[2:] if len(ch_a) > 4 else ch_a[:1] if len(ch_a) > 3 else ch_a
        nm_a = sum(ch_a) / len(ch_a)
        for ch in page['chars']:
            ch['name'] = page_name + '_' + str(ch['cid'])
            r = round(math.sqrt(ch['w'] * ch['h'] / nm_a), 2)
            ch['ratio'] = 0.75 if r < 0.75 else 1.25 if r > 1.25 else r

        chars = {c['name']: c for c in page['chars']}
        columns = {c['column_id']: c for c in page['columns']}
        self.pack_boxes(page, pack_chars=False)
        self.set_char_class(page['chars'])
        img_url = self.get_web_img(page['name'])
        chars_col = self.get_chars_col(page['chars'])
        layout = self.get_query_argument('layout', '')
        template = 'page_txt1.html' if layout == '1' else 'page_txt.html'
        self.render(template, page=page, chars=chars, columns=columns, chars_col=chars_col,
                    txt_types=CharHandler.txt_types, img_url=img_url, readonly=False)
