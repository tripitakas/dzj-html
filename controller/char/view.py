#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from .char import Char
from bson import json_util
from controller import errors as e
from controller.task.task import Task
from controller.base import BaseHandler
from controller.helper import name2code
from controller.task.base import TaskHandler


class CharAdminHandler(BaseHandler, Char):
    URL = '/data/char'

    page_title = '字数据管理'
    search_tips = '请搜索字编码、分类、文字'
    search_fields = ['id', 'source', 'ocr', 'txt']
    table_fields = [
        {'id': 'has_img', 'name': '字图'},
        {'id': 'id', 'name': 'id'},
        {'id': 'source', 'name': '分类'},
        {'id': 'column_cid', 'name': '所属列'},
        {'id': 'ocr', 'name': 'OCR文字'},
        {'id': 'options', 'name': 'OCR候选'},
        {'id': 'txt', 'name': '校对文字'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'log', 'name': '校对记录'},
        {'id': 'remark', 'name': '备注'},
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-gen-img', 'label': '生成字图'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in Task.get_task_types('char').items()
        ]},
    ]
    actions = [
        {'action': 'btn-browse', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    hide_fields = ['log', 'options']
    info_fields = ['has_img', 'source', 'txt', 'txt_type', 'remark']
    update_fields = [
        {'id': 'has_img', 'name': '已有字图', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'source', 'name': '分　　类'},
        {'id': 'txt', 'name': '校对文字'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'remark', 'name': '备　　注'},
    ]
    txt_types = {
        '': '', 'X': '狭义异体字', 'Y': '广义异体字', 'M': '模糊字',
        'N': '拿不准', '*': '不认识',
    }

    def get_duplicate_condition(self):
        chars = list(self.db.char.aggregate([
            {'$group': {'_id': '$id', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'id': {'$in': [c['_id'] for c in chars]}}
        params = {'duplicate': 'true'}
        return condition, params

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""
        if key == 'pos':
            value = '/'.join([str(value.get(f)) for f in ['x', 'y', 'w', 'h']])
        if key == 'has_img' and value:
            value = r'<img class="char-img" src="%s"/>' % self.get_web_img(doc['id'], 'char')
        else:
            value = Task.format_value(value, key)
        return value

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
                        Th=TaskHandler, txt_types=self.txt_types, format_value=self.format_value,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class DataCharBrowseHandler(BaseHandler, Char):
    URL = '/data/char/@char_id'

    def get(self, char_id):
        """ 浏览多张字图"""
        char = self.db.char.find_one({'id': char_id})
        if not char:
            return self.send_error_response(e.no_object, message='没有找到字图%s' % char)
        condition = self.get_char_search_condition(self.request.query)[0]
        op = '$lt' if self.get_query_argument('to', '') == 'prev' else '$lt'
        condition['char_code'] = {op: name2code(char_id)}
        docs, pager, q, order = self.find_by_page(condition, default_order='char_code')
