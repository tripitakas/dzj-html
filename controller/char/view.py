#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bson import json_util
from .char import Char
from .base import CharHandler
from controller import helper as h
from controller import errors as e
from controller.page.base import PageHandler


class CharListHandler(CharHandler):
    URL = '/char/list'

    page_title = '字数据管理'
    table_fields = [
        {'id': 'has_img', 'name': '字图'},
        {'id': 'source', 'name': '分类'},
        {'id': 'page_name', 'name': '页编码'},
        {'id': 'cid', 'name': 'cid'},
        {'id': 'name', 'name': '字编码'},
        {'id': 'char_id', 'name': '字序'},
        {'id': 'uid', 'name': '字序编码'},
        {'id': 'data_level', 'name': '数据等级'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'column', 'name': '所属列'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'txt', 'name': '原字'},
        {'id': 'nor_txt', 'name': '正字'},
        {'id': 'ocr_txt', 'name': 'OCR文字'},
        {'id': 'ocr_col', 'name': '列框OCR'},
        {'id': 'cmp_txt', 'name': '比对文字'},
        {'id': 'alternatives', 'name': '字框OCR'},
        {'id': 'diff', 'name': '是否不匹配'},
        {'id': 'un_required', 'name': '是否不必校对'},
        {'id': 'txt_level', 'name': '文本等级'},
        {'id': 'txt_logs', 'name': '文本校对记录'},
        {'id': 'tasks', 'name': '校对任务'},
        {'id': 'remark', 'name': '备注'},
    ]
    operations = [
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-browse', 'label': '浏览结果'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'source', 'label': '按分类'},
            {'operation': 'txt', 'label': '按原字'},
            {'operation': 'ocr_txt', 'label': '按OCR'},
            {'operation': 'nor_txt', 'label': '按正字'},
        ]},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': name} for k, name in CharHandler.task_names('char', True).items()
        ]},
        {'operation': 'btn-more', 'label': '更多操作', 'groups': [
            {'operation': 'bat-remove', 'label': '批量删除', 'url': '/api/char/delete'},
            {'operation': 'bat-source', 'label': '更新分类'},
            {'operation': 'btn-duplicate', 'label': '查找重复'},
            {'operation': 'bat-gen-img', 'label': '生成字图'},
            {'operation': 'btn-check-consistent', 'label': '检查一致'},
        ]},
    ]
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-remove', 'label': '删除', 'url': '/api/char/delete'},
    ]
    hide_fields = ['page_name', 'cid', 'char_id', 'uid', 'data_level', 'cc', 'sc', 'pos', 'column', 'diff', 'txt_logs',
                   'tasks', 'remark']
    info_fields = ['has_img', 'source', 'txt', 'nor_txt', 'txt_type', 'remark']
    update_fields = [
        {'id': 'txt_type', 'name': '类型', 'input_type': 'radio', 'options': Char.txt_types},
        {'id': 'source', 'name': '分类'},
        {'id': 'txt', 'name': '原字'},
        {'id': 'nor_txt', 'name': '正字'},
        {'id': 'remark', 'name': '备注'},
    ]

    yes_no = {True: '是', False: '否'}

    def get_duplicate_condition(self):
        chars = list(self.db.char.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'name': {'$in': [c['_id'] for c in chars]}}
        params = {'duplicate': 'true'}
        return condition, params

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""

        def log2str(log):
            val = '|'.join(log[f] for f in ['txt', 'nor_txt', 'txt_type', 'remark', 'user_name'] if log.get(f))
            if log.get('updated_time'):
                val = val + '|' + h.get_date_time('%Y-%m-%d %H:%M', log.get('updated_time'))
            return val

        if key == 'pos' and value:
            return '/'.join([str(value.get(f)) for f in ['x', 'y', 'w', 'h']])
        if key == 'txt_type' and value:
            return self.txt_types.get(value, value)
        if key in ['diff', 'un_required']:
            return self.yes_no.get(value) or ''
        if key in ['cc', 'sc'] and value:
            return value / 1000
        if key == 'txt_logs' and value:
            return '<br/>'.join([log2str(log) for log in value])
        if key == 'tasks' and value and isinstance(value, dict):
            return '<br/>'.join(['%s: %s' % (self.get_task_name(typ), len(tasks)) for typ, tasks in value.items()])
        if key == 'has_img' and value not in [None, False]:
            return r'<img class="char-img" src="%s"/>' % self.get_char_img(doc)
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
                condition, params = Char.get_char_search_condition(self.request.query)
            docs, pager, q, order = Char.find_by_page(self, condition)
            self.render('char_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        txt_types=self.txt_types, yes_no=self.yes_no, format_value=self.format_value,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CharViewHandler(CharHandler):
    URL = '/char/@char_name'

    def get(self, char_name):
        """ 查看Char页面"""
        try:
            char = self.db.char.find_one({'name': char_name})
            page_name, cid = char_name.rsplit('_', 1)
            if not char:
                char = {'name': char_name, 'page_name': page_name, 'cid': int(cid), 'error': True}
                # return self.send_error_response(e.no_object, message='没有找到数据%s' % char_name)
            projection = {'name': 1, 'chars.$': 1, 'width': 1, 'height': 1, 'tasks': 1}
            page = self.db.page.find_one({'name': page_name, 'chars.cid': int(cid)}, projection) or {}
            if page:
                c = page['chars'][0]
                c['pos'] = dict(x=c['x'], y=c['y'], w=c['w'], h=c['h'])
                for field in Char.fields:
                    f = field['id']
                    if not char.get(f) and c.get(f):
                        char[f] = c[f]
            char['txt_level'] = char.get('txt_level') or 1
            char['box_level'] = char.get('box_level') or 1
            char['txt_point'] = self.get_required_type_and_point(char)
            char['box_point'] = PageHandler.get_required_type_and_point(page)
            img_url = self.get_web_img(page_name, 'page', page.get('img_cloud_path'))
            txt_auth = self.check_txt_level_and_point(self, char, None, False) is True
            box_auth = PageHandler.check_box_level_and_point(self, char, page, None, False) is True
            chars = {char['name']: char}
            self.render('char_view.html', char=char, page=page, img_url=img_url, chars=chars,
                        txt_auth=txt_auth, box_auth=box_auth, Char=Char)

        except Exception as error:
            return self.send_db_error(error)


class CharStatHandler(CharHandler):
    URL = '/char/statistic'

    def get(self):
        """ 统计字数据"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            kind = self.get_query_argument('kind', '')
            if kind not in ['source', 'txt', 'ocr_txt', 'nor_txt']:
                return self.send_error_response(e.statistic_type_error, message='只能按分类、正字、原字和OCR文字统计')
            aggregates = [{'$group': {'_id': '$' + kind, 'count': {'$sum': 1}}}]
            docs, pager, q, order = Char.aggregate_by_page(self, condition, aggregates, default_order='-count')
            self.render('char_statistic.html', docs=docs, pager=pager, q=q, order=order, kind=kind, Char=Char)

        except Exception as error:
            return self.send_db_error(error)


class CharBrowseHandler(CharHandler):
    URL = '/char/browse'

    page_size = 50

    def get(self):
        """ 浏览字图"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            docs, pager, q, order = Char.find_by_page(self, condition)
            chars = {str(d['name']): d for d in docs}
            for d in docs:
                column_name = '%s_%s' % (d['page_name'], self.prop(d, 'column.cid'))
                d['column']['img_url'] = self.get_web_img(column_name, 'column')
            self.render('char_browse.html', docs=docs, pager=pager, q=q, order=order, chars=chars)

        except Exception as error:
            return self.send_db_error(error)


class CharConsistentHandler(CharHandler):
    URL = '/char/consistent'

    def get(self):
        """ 检查字数据中某页的数据和页数据中字框的数量是否一致"""
        try:

            cond = self.get_char_search_condition(self.request.query)[0]
            counts = list(self.db.char.aggregate([
                {'$match': cond},
                {'$group': {'_id': '$page_name', 'count': {'$sum': 1}}},
            ]))
            page_dict = {c['_id']: {'char_count': c['count']} for c in counts}
            pages = list(self.db.page.aggregate([
                {'$match': {'name': {'$in': list(page_dict.keys())}}},
                {'$project': {'name': 1, 'page_count': {'$size': '$chars'}}}
            ]))
            for p in pages:
                page = page_dict[p['name']]
                page['page_count'] = p['page_count']
                page['equal'] = page['char_count'] == p['page_count']
                page['info'] = '%s,%s,%s' % (p['name'], page['char_count'], p['page_count'])

            un_exist = {k: v for k, v in page_dict.items() if not v.get('page_count')}
            equal = {k: v for k, v in page_dict.items() if v.get('page_count') and v.get('equal')}
            un_equal = {k: v for k, v in page_dict.items() if v.get('page_count') and not v.get('equal')}

            self.render('char_consistent.html', un_equal=un_equal, equal=equal, un_exist=un_exist, count=len(page_dict))

        except Exception as error:
            return self.send_db_error(error)
