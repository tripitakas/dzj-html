#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
from controller import helper as h
from controller import validate as v
from controller.model import Model
from controller.task.task import Task


class Page(Model):
    collection = 'page'
    fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'width', 'name': '宽度'},
        {'id': 'height', 'name': '高度'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'page_code', 'name': '对齐编码'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'blocks', 'name': '栏框数据'},
        {'id': 'columns', 'name': '列框数据'},
        {'id': 'chars', 'name': '字框数据'},
        {'id': 'ocr', 'name': '字框OCR'},
        {'id': 'ocr_col', 'name': '列框OCR'},
        {'id': 'cmp', 'name': '比对文本'},
        {'id': 'txt', 'name': '审定文本'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'chars_col', 'name': '字序'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'lock_box', 'name': '切分锁'},
        {'id': 'lock_txt', 'name': '文本锁'},
        {'id': 'level_box', 'name': '切分等级'},
        {'id': 'level_txt', 'name': '文本等级'},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_txt', 'name': '文本备注'},
    ]
    rules = [
        (v.not_empty, 'name'),
        (v.is_page, 'name'),
        (v.is_sutra, 'uni_sutra_code'),
        (v.is_sutra, 'sutra_code'),
        (v.is_reel, 'reel_code'),
        (v.is_digit, 'reel_page_no')
    ]
    primary = 'name'
    search_tips = '请搜索页编码、分类、页面结构、统一经编码、卷编码'
    search_fields = ['name', 'source', 'layout', 'uni_sutra_code', 'reel_code']
    layouts = ['上下一栏', '上下两栏', '上下三栏', '左右两栏']  # 图片的版面结构

    @classmethod
    def metadata(cls):
        return dict(name='', width='', height='', img_suffix='', page_code='', sutra_code='',
                    uni_sutra_code='', reel_code='', reel_page_no='', lock={}, level={},
                    blocks=[], columns=[], chars=[], ocr='', ocr_col='', text='')

    @classmethod
    def pack_doc(cls, doc):
        for field in ['level-box', 'level-text']:
            if doc.get(field):
                doc[field.replace('-', '.')] = doc[field]
        for field in ['ocr', 'ocr_col', 'text']:
            if doc.get(field):
                doc[field] = re.sub('\n{2,}', '||', doc[field]).replace('\n', '|')
        if doc.get('text'):
            doc['txt_html'] = ''
        return super().pack_doc(doc)

    @classmethod
    def insert_many(cls, db, file_stream=None, layout=None):
        """ 插入新页面
        :param db 数据库连接
        :param file_stream 已打开的文件流。
        :param layout 页面的版面结构。
        :return {status: 'success'/'failed', code: '',  message: '...', errors:[]}
        """
        result = json.load(file_stream)
        page_names = [r.split('.')[0] for r in result]
        name2suffix = {r.split('.')[0]: r.split('.')[1] if '.' in r else None for r in result}
        # 检查重复时，仅仅检查页码，不检查后缀
        existed_pages = list(db.page.find({'name': {'$in': page_names}}, {'name': 1}))
        new_names = set(page_names) - set([p['name'] for p in existed_pages])
        pages = []
        for page_name in new_names:
            page = cls.metadata()
            s = page_name.split('.')
            page['name'] = s[0]
            page['layout'] = layout
            page['page_code'] = h.align_code(s[0])
            page['img_suffix'] = name2suffix.get(page_name)
            pages.append(page)
        if pages:
            r = db.page.insert_many(pages)
        message = '导入page，总共%s条记录，插入%s条，%s条旧数据。' % (len(page_names), len(pages), len(existed_pages))
        return dict(status='success', message=message, inserted_ids=r.inserted_ids if pages else [])

    @classmethod
    def get_page_search_condition(cls, request_query):
        condition, params = dict(), dict()
        q = h.get_url_param('q', request_query)
        if q and cls.search_fields:
            condition['$or'] = [{k: {'$regex': q, '$options': '$i'}} for k in cls.search_fields]
        for field in ['name', 'source', 'remark-box', 'remark-text']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field.replace('-', '.'): {'$regex': value, '$options': '$i'}})
        for field in ['level-box', 'level-text']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                m = re.search(r'([><=]?)(\d+)', value)
                if m:
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m.group(1))
                    condition.update({field.replace('_', '.'): {op: value} if op else value})
        for field in ['cut_proof', 'cut_review', 'text_proof_1', 'text_proof_1', 'text_proof_3', 'text_review']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({'tasks.' + field: None if value == 'un_published' else value})
        value = h.get_url_param('txt', request_query)
        if value:
            params[field] = value
            condition.update({'$or': [{k: {'$regex': value}} for k in ['ocr', 'ocr_col', 'text']]})
        return condition, params

    @staticmethod
    def format_value(value, key=None, doc=None):
        """ 格式化page表的字段输出"""
        if key == 'tasks':
            value = value or {}
            tasks = ['%s/%s' % (Task.get_task_name(k), Task.get_status_name(v)) for k, v in value.items()]
            return '<br/>'.join(tasks)
        if key in ['lock-box', 'lock-text']:
            if h.prop(value, 'is_temp') is not None:
                return '临时锁<a>解锁</a>' if h.prop(value, 'is_temp') else '任务锁'
        return h.format_value(value, key)


class Char(Model):
    collection = 'char'
    fields = [
        {'id': 'name', 'name': '字编码'},
        {'id': 'page_name', 'name': '页编码'},
        {'id': 'char_id', 'name': 'char_id'},
        {'id': 'uid', 'name': 'uid', 'remark': 'page_name和char_id的整型值'},
        {'id': 'cid', 'name': 'cid'},
        {'id': 'source', 'name': '分类'},
        {'id': 'has_img', 'name': '是否已有字图'},
        {'id': 'img_need_updated', 'name': '是否需要更新字图'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'column', 'name': '所属列'},
        {'id': 'ocr_txt', 'name': '字框OCR'},
        {'id': 'col_txt', 'name': '列框OCR'},
        {'id': 'cmp_txt', 'name': '比对文字'},
        {'id': 'alternatives', 'name': 'OCR候选'},
        {'id': 'txt', 'name': '正字'},
        {'id': 'ori_txt', 'name': '原字'},
        {'id': 'txt_type', 'name': '类型'},
        {'id': 'box_level', 'name': '切分等级'},
        {'id': 'box_logs', 'name': '切分校对历史'},
        {'id': 'box_count', 'name': '切分校对次数'},
        {'id': 'txt_level', 'name': '文字等级'},
        {'id': 'txt_logs', 'name': '文字校对历史'},
        {'id': 'txt_count', 'name': '文字校对次数'},
        {'id': 'remark', 'name': '备注'},
    ]
    rules = [
        (v.is_page, 'page_name'),
    ]
    primary = 'name'

    txt_types = {'': '正字', 'Y': '广义异体字', 'X': '狭义异体字', 'M': '模糊或残损', 'N': '不确定', '*': '不认识'}
    # search_fields在这里定义，这样find_by_page时q参数才会起作用
    search_tips = '请搜索字编码、分类、文字'
    search_fields = ['name', 'source', 'txt', 'ocr_txt', 'ori_txt']

    @classmethod
    def get_char_search_condition(cls, request_query):
        def c2int(c):
            return int(float(c) * 1000)

        condition, params = dict(), dict()
        for field in ['txt', 'ocr_txt', 'txt_type']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        for field in ['name', 'source', 'remark']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
        for field in ['cc', 'sc']:
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
