#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
from controller import auth
from controller import errors as e
from controller import helper as h
from controller.task.task import Task
from controller.page.page import Page
from controller.page.base import PageHandler
from controller.char.base import CharHandler


class PageListHandler(PageHandler):
    URL = '/page/list'

    page_title = '页数据管理'
    table_fields = ['name', 'page_code', 'book_page', 'source', 'layout', 'uni_sutra_code', 'sutra_code',
                    'reel_code', 'tasks', 'remark_box', 'remark_txt', 'txt_match']
    update_fields = ['source', 'layout', 'remark_box', 'remark_txt']
    hide_fields = ['book_page', 'uni_sutra_code', 'sutra_code', 'reel_code', 'remark_box', 'remark_txt', 'txt_match']
    operations = [
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': name} for k, name in PageHandler.task_names('page', True, False).items()
        ]},
        {'operation': 'btn-more', 'label': '更多操作', 'groups': [
            {'operation': 'bat-delete', 'label': '批量删除'},
            {'operation': 'bat-source', 'label': '更新分类'},
            {'operation': 'btn-statistic', 'label': '统计分类'},
            {'operation': 'btn-duplicate', 'label': '查找重复'},
            {'operation': 'bat-gen-chars', 'label': '生成字数据'},
        ]},
    ]
    actions = [
        {'action': 'btn-box', 'label': '切分'},
        {'action': 'btn-text', 'label': '文本'},
        {'action': 'btn-browse', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-update', 'label': '更新', 'url': '/api/page/meta'},
        {'action': 'btn-delete', 'label': '删除'},
    ]
    task_statuses = {
        '': '', 'un_published': '未发布', 'published': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }
    match_fields = {'': '', 'cmp_txt': '比对文本', 'ocr_col': '列框OCR', 'txt': '校对文本'}
    match_statuses = {'': '', None: '无', True: '匹配', False: '不匹配'}

    def get_template_kwargs(self, fields=None):
        kwargs = super(Page, self).get_template_kwargs()
        kwargs['hide_fields'] = self.get_hide_fields() or kwargs['hide_fields']
        if '系统管理员' in self.current_user['roles']:
            kwargs['operations'][-2]['groups'] = [
                {'operation': k, 'label': name} for k, name in PageHandler.task_names('page', True, True).items()
            ]
        return kwargs

    def format_value(self, value, key=None, doc=None):
        """格式化page表的字段输出"""

        def format_txt(field, show_none=True):
            s = {True: '√', False: '×', None: ''}.get(self.prop(doc, 'txt_match.%s.status' % field))
            if self.get_txt(doc, field):
                return '<a title="%s">%s%s</a>' % (field, self.match_fields.get(field), s)
            return '<a title="%s">%s%s(无)</a>' % (field, self.match_fields.get(field), s) if show_none else ''

        if key == 'tasks' and value:
            ret = ''
            for tsk_type, tasks in value.items():
                if isinstance(tasks, dict):
                    for num, status in tasks.items():
                        ret += '%s#%s/%s<br/>' % (self.get_task_name(tsk_type), num, self.get_status_name(status))
                else:
                    ret += '%s/%s<br/>' % (self.get_task_name(tsk_type), self.get_status_name(tasks))
            return ret.rstrip('<br/>')
        if key == 'txt_match':
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
        """页数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = Page.get_page_search_condition(self.request.query)
            page_tasks = {'': '', **PageHandler.task_names('page', True, True)}
            docs, pager, q, order = Page.find_by_page(self, condition)
            self.render('page_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        match_fields=self.match_fields, match_statuses=self.match_statuses,
                        page_tasks=page_tasks, task_statuses=self.task_statuses,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageBoxHandler(PageHandler):
    URL = '/page/box/@page_name'

    def get(self, page_name):
        """切分校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            self.pack_cut_boxes(page)
            self.set_box_access(page)
            page['img_url'] = self.get_page_img(page)
            roles = auth.get_all_roles(self.current_user['roles'])
            box_auth = self.check_open_edit_role(roles) is True
            self.render('page_box.html', page=page, readonly=not box_auth)

        except Exception as error:
            return self.send_db_error(error)


class PageTxtHandler(PageHandler):
    URL = '/page/txt/@page_name'

    def get(self, page_name):
        """单字修改页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            self.pack_txt_boxes(page)
            page['img_url'] = self.get_page_img(page)
            roles = auth.get_all_roles(self.current_user['roles'])
            txt_auth = CharHandler.check_open_edit_role(roles) is True
            self.render('page_txt.html', page=page, readonly=not txt_auth)

        except Exception as error:
            return self.send_db_error(error)


class PageTxt1Handler(PageHandler):
    URL = '/page/txt1/@page_name'

    def get(self, page_name):
        """单字修改页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            self.pack_txt_boxes(page)
            # 设置class属性
            self.set_char_class(page['chars'])
            # 设置name、txt以及ratio
            ch_a = sorted([c['w'] * c['h'] for c in page['chars']])
            ch_a = ch_a[:-2] if len(ch_a) > 4 else ch_a[:-1] if len(ch_a) > 3 else ch_a
            ch_a = ch_a[2:] if len(ch_a) > 4 else ch_a[:1] if len(ch_a) > 3 else ch_a
            nm_a = sum(ch_a) / len(ch_a)
            for ch in page['chars']:
                ch['name'] = page['name'] + '_' + str(ch['cid'])
                ch['alternatives'] = (ch.get('alternatives') or '').replace('"', '').replace("'", '')
                ch['ocr_txt'] = ch.get('ocr_txt', '').replace('"', '').replace("'", '')
                ch['txt'] = ch.get('txt', '').replace('"', '').replace("'", '')
                ch['txt'] = ch['txt'] or ch['ocr_txt'] or '■'
                r = round(math.sqrt(ch['w'] * ch['h'] / nm_a), 2)
                ch['ratio'] = 0.75 if r < 0.75 else 1.25 if r > 1.25 else r

            img_url = self.get_page_img(page)
            chars = {c['name']: c for c in page['chars']}
            columns = {c['column_id']: c for c in page['columns']}
            self.render('page_txt1.html', page=page, chars=chars, columns=columns,
                        img_url=img_url, readonly=False)

        except Exception as error:
            return self.send_db_error(error)


class PageBrowseHandler(PageHandler):
    URL = '/page/browse/@page_name'

    def get(self, page_name):
        """浏览页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            cond = self.get_page_search_condition(self.request.query)[0]
            order = self.get_query_argument('order', '_id')
            to = self.get_query_argument('to', '')
            if to == 'next':
                cond[order] = {'$gt': page.get(order)}
                page = self.db.page.find_one(cond, sort=[(order, 1)])
            elif to == 'prev':
                cond[order] = {'$lt': page.get(order)}
                page = self.db.page.find_one(cond, sort=[(order, -1)])
            if not page:
                message = '已是第一页' if to == 'prev' else '已是最后一页'
                return self.send_error_response(e.no_object, message=message)

            self.pack_txt_boxes(page)
            page['img_url'] = self.get_page_img(page)
            self.render('page_browse.html', page=page)

        except Exception as error:
            return self.send_db_error(error)


class PageFindCmpHandler(PageHandler):
    URL = '/page/find_cmp/@page_name'

    def get(self, page_name):
        """寻找比对文本页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.pack_txt_boxes(page)
            page['img_url'] = self.get_page_img(page)
            self.render('page_find_cmp.html', page=page, readonly=True, ocr=self.get_txt(page, 'ocr'),
                        cmp_txt=self.get_txt(page, 'cmp_txt'))

        except Exception as error:
            return self.send_db_error(error)


class PageInfoHandler(PageHandler):
    URL = '/page/info/@page_name'

    def format_value(self, value, key=None, doc=None):
        """格式化输出"""
        if key in ['blocks', 'columns', 'chars'] and value:
            return '<div>%s</div>' % '</div><div>'.join([str(v) for v in value])
        return h.format_value(value, key, doc)

    def get(self, page_name):
        """页面详情"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            page_tasks = self.prop(page, 'tasks') or {}
            fields1 = ['txt', 'nor_txt', 'ocr_chr', 'ocr_col', 'cmp_txt']
            page_txts = {k: self.get_txt(page, k) for k in fields1 if self.get_txt(page, k)}
            fields2 = ['blocks', 'columns', 'chars', 'images', 'user_links', 'chars_col']
            page_boxes = {k: self.prop(page, k) for k in fields2 if self.prop(page, k)}
            fields3 = list(set(page.keys()) - set(fields1 + fields2) - {'bak', 'tasks', 'txt_match'})
            metadata = {k: self.prop(page, k) for k in fields3 if self.prop(page, k)}

            self.render('page_info.html', Page=Page, Task=Task, page=page, metadata=metadata,
                        page_txts=page_txts, page_boxes=page_boxes, page_tasks=page_tasks,
                        format_value=self.format_value)

        except Exception as error:
            return self.send_db_error(error)


class PageStatisticHandler(PageHandler):
    URL = '/page/statistic'

    def get(self):
        """统计分类"""
        try:
            counts = list(self.db.page.aggregate([{'$group': {'_id': '$source', 'count': {'$sum': 1}}}]))
            self.render('data_statistic.html', counts=counts, collection='page')

        except Exception as error:
            return self.send_db_error(error)


class PageTxtMatchHandler(PageHandler):
    URL = '/page/txt_match/@page_name'

    def get(self, page_name):
        """文字匹配页面。（将文本和OCR字框文本适配后，回写至字框中）"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            field = self.get_query_argument('field', '')
            assert field in ['txt', 'cmp_txt', 'ocr_col']
            txt_match = self.prop(page, 'txt_match.' + field)
            mth_txt = self.prop(txt_match, 'value') or self.get_txt(page, field)
            field_name = Page.get_field_name(field)
            if not mth_txt:
                if field == 'cmp_txt':
                    self.redirect('/page/find_cmp/' + page_name)
                else:
                    self.send_error_response(e.no_object, message='页面没有%s，无法进行匹配' % field_name)

            ocr_txt = self.get_txt(page, 'ocr')
            txts = [(mth_txt, field, field_name), (ocr_txt, 'ocr', '字框OCR')]
            txt_dict = {t[1]: t for t in txts}
            cmp_data = self.match_diff(ocr_txt, mth_txt)
            self.pack_txt_boxes(page, False)
            img_url = self.get_page_img(page)
            self.render(
                'page_txt_match.html', page=page, img_url=img_url, ocr_txt=ocr_txt, cmp_data=cmp_data,
                field=field, field_name=field_name, txt_match=txt_match, txts=txts,
                txt_fields=[field, 'OCR'], txt_dict=txt_dict, active='work-html',
            )

        except Exception as error:
            return self.send_db_error(error)
