#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from controller.model import Model
from controller import helper as h
from controller import validate as v
from controller.tool import variant as vt


class Char(Model):
    primary = 'name'
    collection = 'char'
    fields = {
        'name': {'name': '字编码'},
        'page_name': {'name': '页编码'},
        'char_id': {'name': '字序号'},
        'uid': {'name': '对齐编码', 'remark': 'page_name和char_id'},
        'cid': {'name': 'cid'},
        'source': {'name': '分类'},
        'has_img': {'name': '字图'},
        'img_need_updated': {'name': '需要更新字图'},
        'pos': {'name': '坐标'},
        'column': {'name': '所属列'},
        'cc': {'name': '字置信度'},
        'lc': {'name': '列置信度'},
        'pc': {'name': '校对等级'},
        'sc': {'name': '相同程度'},
        'alternatives': {'name': '字OCR候选'},
        'ocr_txt': {'name': '字框OCR'},
        'ocr_col': {'name': '列框OCR'},
        'cmp_txt': {'name': '比对文字'},
        'cmb_txt': {'name': '综合OCR'},
        'txt': {'name': '校对文字'},
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
    # 相同程度
    equal_level = {
        '39': '三字相同', '28': '两同一异', '6': '三字不同', '29': '两字相同', '18': '两字不同',
        '9': '仅有一字', '0': '没有文本'
    }
    # 校对等级
    proof_level = {
        '39000': '三字相同', '06000': '三字不同',
        '28005': '字比同-列异文', '28105': '字比同-列异体', '28015': '字比同-列候选', '28115': '字比同-列候异',
        '28003': '字列同-比异文', '28103': '字列同-比异体', '28013': '字列同-比候选', '28113': '字列同-比候异',
        '28000': '列比同-字异文', '28100': '列比同-字异体', '28010': '列比同-字候选', '28110': '列比同-字候异',
        '29005': '无列-字比同', '29003': '无比-字列同', '29000': '无字-列比同',
        '07005': '无列-字比异文', '07105': '无列-字比异体', '07015': '无列-字比候选', '07115': '无列-字比候异',
        '07003': '无比-字列异文', '07103': '无比-字列异体', '07013': '无比-字列候选', '07113': '无比-字列候异',
        '07000': '无字-列比异文', '07100': '无字-列比异体', '07010': '无字-列比候选', '07110': '无字-列比候异',
        '08005': '仅有字文', '08003': '仅有列文', '08000': '仅有比文', '00000': '没有文本'
    }

    @staticmethod
    def is_valid_txt(txt):
        return txt not in [None, '■', '']

    @classmethod
    def get_cmb_txt(cls, ch):
        """ 选择综合文本"""
        insist_ocr = {'衆': '眾', '説': '說', '従': '從', '塲': '場', '隂': '陰'}
        cmb_txt = (ch.get('alternatives') or '')[:1]
        if cls.is_valid_txt(ch.get('cmp_txt')) and cmb_txt != ch['cmp_txt']:
            if ch['cmp_txt'] == ch.get('ocr_col') or ch['cmp_txt'] in (ch.get('alternatives') or ''):
                if not (cmb_txt in insist_ocr and ch['cmp_txt'] == insist_ocr[cmb_txt]):
                    cmb_txt = ch['cmp_txt']
        return cmb_txt

    @classmethod
    def get_equal_level(cls, ch):
        """ 获取相同等级"""
        ocr_txt, ocr_col, cmp_txt = (ch.get('alternatives') or '')[:1], ch.get('ocr_col'), ch.get('cmp_txt')
        valid = [t for t in [ocr_txt, ocr_col, cmp_txt] if cls.is_valid_txt(t)]
        uni = len(set(valid))
        if len(valid) == 3:
            if uni == 1:  # 三字相同
                return 39
            if uni == 2:  # 两同一异
                return 28
            if uni == 3:  # 三字不同
                return 6
        elif len(valid) == 2:
            if uni == 1:  # 两字相同
                return 29
            if uni == 2:  # 两字不同
                return 18
        elif len(valid) == 1:
            return 9  # 仅有一字
        else:
            return 0  # 没有文本

    @classmethod
    def get_prf_level(cls, ch):
        """ 获取校对等级、相同等级"""

        ocr_txt, ocr_col, cmp_txt = (ch.get('alternatives') or '')[:1], ch.get('ocr_col'), ch.get('cmp_txt')
        valid = [t for t in [ocr_txt, ocr_col, cmp_txt] if cls.is_valid_txt(t)]
        pc, uni = '', len(set(valid))
        if len(valid) == 3:
            if uni == 1:  # 三字相同
                pc = '39000'
            elif uni == 2:  # 两同一异
                if ocr_txt == cmp_txt:
                    x = '1' if vt.is_variant(ocr_txt, ocr_col) else '0'
                    y = '1' if ocr_col in (ch.get('alternatives') or '') else '0'
                    pc = '28%s%s5' % (x, y)
                elif ocr_txt == ocr_col:
                    x = '1' if vt.is_variant(ocr_txt, cmp_txt) else '0'
                    y = '1' if cmp_txt in (ch.get('alternatives') or '') else '0'
                    pc = '28%s%s3' % (x, y)
                elif ocr_col == cmp_txt:
                    x = '1' if vt.is_variant(ocr_txt, cmp_txt) else '0'
                    y = '1' if cmp_txt in (ch.get('alternatives') or '') else '0'
                    pc = '28%s%s0' % (x, y)
            elif uni == 3:  # 三字不同
                pc = int('06000')
        elif len(valid) == 2:
            if cls.is_valid_txt(ocr_txt) and cls.is_valid_txt(cmp_txt):  # 字比存在，系统调整量为5
                if ocr_txt == cmp_txt:
                    pc = '29005'
                else:
                    x = '1' if vt.is_variant(ocr_txt, cmp_txt) else '0'
                    y = '1' if cmp_txt in (ch.get('alternatives') or '') else '0'
                    pc = '07%s%s5' % (x, y)
            elif cls.is_valid_txt(ocr_txt) and cls.is_valid_txt(ocr_col):  # 字列存在，系统调整量为3
                if ocr_txt == ocr_col:
                    pc = '29003'
                else:
                    x = '1' if vt.is_variant(ocr_txt, ocr_col) else '0'
                    y = '1' if ocr_col in (ch.get('alternatives') or '') else '0'
                    pc = '07%s%s3' % (x, y)
            elif cls.is_valid_txt(cmp_txt) and cls.is_valid_txt(ocr_col):  # 比列存在，系统调整量为0
                if cmp_txt == ocr_col:
                    pc = '29000'
                else:
                    x = '1' if vt.is_variant(cmp_txt, ocr_col) else '0'
                    pc = '07%s%s0' % (x, 0)
        elif len(valid) == 1:
            if cls.is_valid_txt(ocr_txt):
                pc = '08005'
            elif cls.is_valid_txt(cmp_txt):
                pc = '08003'
            else:
                pc = '08000'
        else:
            pc = '00000'
        return int(pc)

    @classmethod
    def get_char_search_condition(cls, request_query):
        def c2int(c):
            return int(float(c) * 1000)

        condition, params = dict(), dict()
        q = h.get_url_param('q', request_query)
        if q and cls.search_fields:
            m = len(q) > 1 and q[0] == '='
            condition['$or'] = [{k: q[1:] if m else {'$regex': q}} for k in cls.search_fields]
        for field in ['cmb_txt', 'txt']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
                if 'v' in value:  # v_code
                    condition.update({field: value[1:] if value[0] == '=' else {'$regex': value}})
        for field in ['is_vague', 'is_deform', 'uncertain']:
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
        for field in ['pc', 'sc']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                m1 = re.search(r'^([><]=?)?(\d+)$', value)
                op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m1.group(1))
                condition.update({field: {op: int(m1.group(2))} if op else int(value)})
        for field in ['cc', 'lc']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                m1 = re.search(r'^([><]=?)(0|1|[01]\.\d+)$', value)
                m2 = re.search(r'^(0|1|[01]\.\d+),(0|1|[01]\.\d+)$', value)
                if m1:
                    print(field, value)
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m1.group(1))
                    condition.update({field: {op: c2int(m1.group(2))} if op else value})
                elif m2:
                    condition.update({field: {'$gte': c2int(m2.group(1)), '$lte': c2int(m2.group(2))}})
        return condition, params
