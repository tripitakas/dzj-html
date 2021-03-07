#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from .char import Char
from bson import json_util
from .base import CharHandler
from controller import helper as h
from controller import errors as e
from controller.page.base import PageHandler


class CharListHandler(CharHandler):
    URL = '/char/list'

    page_title = '字数据管理'
    table_fields = ['has_img', 'source', 'page_name', 'name', 'char_id', 'uid', 'pos', 'box_level', 'column',
                    'alternatives', 'ocr_col', 'cmp_txt', 'cmb_txt', 'cc', 'lc', 'sc', 'pc',
                    'is_vague', 'is_deform', 'uncertain', 'txt', 'nor_txt', 'remark',
                    'txt_level', 'txt_logs', 'tasks', 'updated_time']
    update_fields = ['source', 'txt', 'is_vague', 'is_deform', 'uncertain', 'remark']
    hide_fields = ['page_name', 'char_id', 'uid', 'pos', 'box_level', 'column', 'cc', 'lc', 'pc',
                   'is_vague', 'is_deform', 'uncertain', 'nor_txt', 'remark',
                   'txt_logs', 'tasks', 'updated_time']
    info_fields = ['source', 'txt', 'is_vague', 'is_deform', 'uncertain', 'remark']
    operations = [
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-browse', 'label': '浏览结果'},
        {'operation': 'btn-statistic', 'label': '结果统计', 'groups': [
            {'operation': 'source', 'label': '按分类'},
            {'operation': 'txt', 'label': '按校对文字'},
            {'operation': 'cmb_txt', 'label': '按综合OCR'},
        ]},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': name} for k, name in CharHandler.task_names('char', True).items()
        ]},
        {'operation': 'btn-more', 'label': '更多操作', 'groups': [
            {'operation': 'bat-remove', 'label': '批量删除', 'url': '/api/char/delete'},
            {'operation': 'bat-source', 'label': '更新分类'},
            {'operation': 'btn-duplicate', 'label': '查找重复'},
            {'operation': 'bat-gen-imgs', 'label': '生成字图'},
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
        if key in ['sc'] and value:
            return self.equal_level.get(str(value)) or ''
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
            if self.get_hide_fields() is not None:
                kwargs['hide_fields'] = self.get_hide_fields()
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
            page_name, cid = char_name.rsplit('_', 1)
            project = {'name': 1, 'chars': 1, 'width': 1, 'height': 1, 'tasks': 1}
            page = self.db.page.find_one({'name': page_name}, project)
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            chars = [c for c in page.get('chars') or [] if str(c['cid']) == cid]
            if not chars:
                self.send_error_response(e.no_object, message='页面%s中没有字符%s' % (page_name, cid))
            ch = chars[0]
            char = self.db.char.find_one({'name': char_name})
            if char:
                char.update({k: ch[k] for k in ['x', 'y', 'w', 'h', 'box_level', 'box_logs'] if ch.get(k)})
            else:
                char = ch
            if not char.get('x') and char.get('pos'):
                char.update(char['pos'])
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
            cond = Char.get_char_search_condition(self.request.query)[0]
            kind = self.get_query_argument('kind', '')
            if kind not in ['source', 'txt', 'cmb_txt']:
                return self.send_error_response(e.statistic_type_error, message='只能按分类、校对文字和综合OCR统计')
            aggregates = [{'$group': {'_id': '$' + kind, 'count': {'$sum': 1}}}]
            docs, pager, q, order = Char.aggregate_by_page(self, cond, aggregates, default_order='-count')
            self.render('char_statistic.html', docs=docs, pager=pager, q=q, order=order, kind=kind, Char=Char)

        except Exception as error:
            return self.send_db_error(error)


class CharBrowseHandler(CharHandler):
    URL = '/char/browse'

    page_size = 50  # find_by_page据此来设置每页条数

    def get(self):
        """浏览字图"""
        try:
            cond = self.get_user_filter()
            cond.update(self.get_char_search_condition(self.request.query)[0])
            self.page_size = int(json_util.loads(self.get_secure_cookie('char_browse_size') or '50'))
            chars, pager, q, order = Char.find_by_page(self, cond, default_order='_id')
            # 设置单字列图
            for ch in chars:
                column_name = '%s_%s' % (ch['page_name'], self.prop(ch, 'column.cid'))
                ch['column']['img_url'] = self.get_web_img(column_name, 'column')
                ch['img_url'] = self.get_web_img(ch['name'], 'char')

            self.render('char_browse.html', chars=chars, pager=pager, q=q, order=order,
                        equal_level=self.equal_level)

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
