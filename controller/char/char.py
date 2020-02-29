#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import json
from controller.model import Model
from controller import validate as v
from controller.helper import get_url_param, prop, name2code


class Char(Model):
    collection = 'char'
    fields = [
        {'id': 'page_name', 'name': '页编码'},
        {'id': 'cid', 'name': 'cid'},
        {'id': 'column_cid', 'name': '所属列'},
        {'id': 'char_id', 'name': 'id'},
        {'id': 'char_code', 'name': 'code'},
        {'id': 'source', 'name': '分类'},
        {'id': 'has_img', 'name': '字图'},
        {'id': 'ocr', 'name': 'OCR文字'},
        {'id': 'options', 'name': 'OCR候选'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'txt', 'name': '校对文字'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'log', 'name': '校对记录'},
        {'id': 'remark', 'name': '备注'},
    ]
    rules = [
        (v.is_page, 'page_name'),
    ]
    primary = 'id'

    @staticmethod
    def get_char_search_condition(request_query):
        condition, params = dict(), dict()
        for field in ['ocr', 'txt', 'txt_type']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        for field in ['char_id', 'source', 'remark']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
        for field in ['cc', 'sc']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                m = re.search(r'([><=]?)(\d+)', value)
                if m:
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m.group(1))
                    condition.update({field: {op: value} if op else value})
        return condition, params
