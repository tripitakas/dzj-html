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
    table_fields = ['has_img', 'source', 'page_name', 'cid', 'name', 'char_id', 'uid', 'box_level', 'cc', 'lc',
                    'pos', 'column', 'alternatives', 'ocr_col', 'cmp_txt', 'ocr_txt', 'diff', 'un_required',
                    'is_vague', 'is_deform', 'uncertain', 'txt', 'nor_txt', 'txt_level', 'txt_logs',
                    'tasks', 'remark']
    update_fields = ['source', 'txt', 'nor_txt', 'is_vague', 'is_deform', 'uncertain', 'remark']
    hide_fields = ['page_name', 'cid', 'char_id', 'uid', 'box_level', 'cc', 'lc', 'pos', 'column', 'diff',
                   'un_required', 'is_vague', 'is_deform', 'uncertain', 'txt_logs', 'tasks', 'remark']
    info_fields = ['source', 'txt', 'nor_txt', 'is_vague', 'is_deform', 'uncertain', 'remark']
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
        {'action': 'btn-my-view', 'label': '查看'},
        {'action': 'btn-remove', 'label': '删除', 'url': '/api/char/delete'},
    ]

    def get_duplicate_condition(self):
        chars = list(self.db.char.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'name': {'$in': [c['_id'] for c in chars]}}
        params = {'duplicate': 'true'}
        return condition, params

    def format_value(self, value, key=None, doc=None):
        """格式化page表的字段输出"""

        def log2str(log):
            val, log_time = [], log.get('updated_time') or log.get('create_time')
            log_time and val.append(h.get_date_time('%Y-%m-%d %H:%M:%S', log_time))
            log.get('username') and val.append('@' + log['username'] + ': ')
            log.get('txt') and val.append(log['txt'])
            val.extend(['/' + self.get_field_name(f) for f in ['is_vague', 'is_deform', 'uncertain'] if log.get(f)])
            log.get('remark') and val.append('/' + log['remark'])
            return ''.join(val)

        if key == 'pos' and value:
            return '/'.join([str(value.get(f)) for f in ['x', 'y', 'w', 'h']])
        if key in ['diff', 'un_required']:
            return self.yes_no.get(value) or ''
        if key in ['cc', 'lc'] and value:
            return value / 1000
        if key == 'txt_logs' and value:
            return '<br/>'.join([log2str(log) for log in value])
        if key == 'tasks' and value and isinstance(value, dict):
            return '<br/>'.join(['%s: %s' % (self.get_task_name(typ), len(tasks)) for typ, tasks in value.items()])
        if key == 'has_img' and value not in [None, False]:
            return r'<img class="char-img" src="%s"/>' % self.get_char_img(doc)
        return h.format_value(value, key, doc)

    def get(self):
        """字数据管理"""
        try:
            kwargs = super(Char, self).get_template_kwargs()
            kwargs['hide_fields'] = self.get_hide_fields() or kwargs['hide_fields']
            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = Char.get_char_search_condition(self.request.query)
            docs, pager, q, order = Char.find_by_page(self, condition)
            self.render('char_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        yes_no=self.yes_no, format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class CharViewHandler(CharHandler):
    URL = '/char/@char_name'

    def get(self, char_name):
        """查看Char页面"""
        try:
            char = self.db.char.find_one({'name': char_name})
            page_name, cid = char_name.rsplit('_', 1)
            if not char:
                char = {'name': char_name, 'page_name': page_name, 'cid': int(cid), 'error': True}
            project = {'name': 1, 'chars.$': 1, 'width': 1, 'height': 1, 'tasks': 1}
            page = self.db.page.find_one({'name': page_name, 'chars.cid': int(cid)}, project) or {}
            if page:
                c = page['chars'][0]
                if char.get('error'):
                    char.update(c)
                    char.pop('error', 0)
                else:
                    char.update({k: c[k] for k in ['x', 'y', 'w', 'h', 'box_logs'] if c.get(k)})
            char['txt_level'] = char.get('txt_level') or 1
            char['box_level'] = char.get('box_level') or 1
            char['txt_point'] = self.get_required_type_and_point(char)
            char['box_point'] = PageHandler.get_required_type_and_point(page)
            txt_auth = self.check_txt_level_and_point(self, char, None, False) is True
            box_auth = PageHandler.check_box_level_and_point(self, char, page, None, False) is True
            page['img_url'] = self.get_web_img(page_name, 'page')
            self.render('char_view.html', Char=Char, char=char, page=page, txt_auth=txt_auth, box_auth=box_auth)

        except Exception as error:
            return self.send_db_error(error)


class CharInfoHandler(CharHandler):
    URL = '/char/info/@char_name'

    @classmethod
    def format_value(cls, value, key=None, doc=None):
        """格式化字段输出"""
        if key in ['pos', 'column'] and value:
            return ','.join(['%s: %s' % (k, v) for k, v in value.items()])
        return h.format_value(value, key, doc)

    def get(self, char_name):
        """查看Char信息"""
        try:
            page_name, cid = char_name.rsplit('_', 1)
            char = self.db.char.find_one({'name': char_name}) or {}
            project = {'name': 1, 'chars.$': 1, 'width': 1, 'height': 1, 'tasks': 1}
            page = self.db.page.find_one({'name': page_name, 'chars.cid': int(cid)}, project)
            p_char = page and page.get('chars') and page['chars'][0] or {}
            self.render('char_info.html', Char=Char, char=char, p_char=p_char, char_name=char_name,
                        format_value=self.format_value)

        except Exception as error:
            return self.send_db_error(error)


class CharStatHandler(CharHandler):
    URL = '/char/statistic'

    def get(self):
        """统计字数据"""
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

    page_size = 50  # find_by_page据此来设置每页条数

    def get(self):
        """浏览字图"""
        try:
            condition = Char.get_char_search_condition(self.request.query)[0]
            docs, pager, q, order = Char.find_by_page(self, condition, default_order='_id')
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
        """检查字数据中某页的数据和页数据中字框的数量是否一致"""
        try:
            cond = self.get_char_search_condition(self.request.query)[0]
            counts = list(self.db.char.aggregate([
                {'$match': cond}, {'$group': {'_id': '$page_name', 'count': {'$sum': 1}}}
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
