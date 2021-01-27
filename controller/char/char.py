#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from controller.model import Model
from controller import helper as h
from controller import validate as v


class Char(Model):
    primary = 'name'
    collection = 'char'
    fields = {
        'name': {'name': '字编码'},
        'page_name': {'name': '页编码'},
        'char_id': {'name': '序号'},
        'uid': {'name': 'uid', 'remark': '对齐编码'},
        'cid': {'name': 'cid'},
        'source': {'name': '分类'},
        'has_img': {'name': '字图'},
        'img_need_updated': {'name': '需要更新字图'},
        'cc': {'name': '字置信度'},
        'lc': {'name': '列置信度'},
        'pc': {'name': '校对等级'},
        'sc': {'name': '相同程度'},
        'pos': {'name': '坐标'},
        'column': {'name': '所属列'},
        'alternatives': {'name': '字框OCR'},
        'ocr_col': {'name': '列框OCR'},
        'cmp_txt': {'name': '比对文字'},
        'ocr_txt': {'name': '综合OCR'},
        'is_diff': {'name': '不一致'},
        'un_required': {'name': '不必校对'},
        'txt': {'name': '原字'},
        'nor_txt': {'name': '正字'},
        'is_vague': {'name': '笔画残损'},
        'is_deform': {'name': '异形字'},
        'uncertain': {'name': '不确定'},
        'box_level': {'name': '切分等级'},
        'box_point': {'name': '切分积分'},
        'box_logs': {'name': '切分校对历史'},
        'txt_level': {'name': '文字等级'},
        'txt_point': {'name': '文字积分'},
        'txt_logs': {'name': '文字校对历史'},
        'tasks': {'name': '校对任务'},
        'remark': {'name': '备注'},
        'updated_time': {'name': '更新时间'},
    }
    rules = [(v.is_page, 'page_name')]
    # search_fields在这里定义，这样find_by_page时q参数才会起作用
    search_fields = ['name', 'source']

    @classmethod
    def get_char_search_condition(cls, request_query):
        def c2int(c):
            return int(float(c) * 1000)

        condition, params = dict(), dict()
        q = h.get_url_param('q', request_query)
        if q and cls.search_fields:
            m = len(q) > 1 and q[0] == '='
            condition['$or'] = [{k: q[1:] if m else {'$regex': q}} for k in cls.search_fields]
        for field in ['ocr_txt']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        for field in ['txt']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
                if 'v' in value:  # v_code
                    condition.update({field: value[1:] if value[0] == '=' else {'$regex': value}})
        for field in ['is_diff', 'un_required', 'is_vague', 'is_deform', 'uncertain']:
            value = h.get_url_param(field, request_query)
            if value:
                trans = {'True': True, 'False': False, 'None': None}
                value = trans.get(value) if value in trans else value
                params[field] = value
                condition.update({field: value})
        for field in ['name', 'source', 'remark']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value[1:] if len(value) > 1 and value[0] == '=' else {'$regex': value}})
        for field in ['cc', 'lc', 'pc', 'sc']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                m1 = re.search(r'^([><]=?)(0|1|[01]\.\d+)$', value)
                m2 = re.search(r'^(0|1|[01]\.\d+),(0|1|[01]\.\d+)$', value)
                if m1:
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m1.group(1))
                    condition.update({field: {op: c2int(m1.group(2))} if op else value})
                elif m2:
                    condition.update({field: {'$gte': c2int(m2.group(1)), '$lte': c2int(m2.group(2))}})

        return condition, params
