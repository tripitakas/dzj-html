#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import json
from functools import cmp_to_key
from controller.model import Model
from controller import helper as h
from controller import validate as v
from controller.task.task import Task


class Tripitaka(Model):
    collection = 'tripitaka'
    fields = [
        {'id': 'tripitaka_code', 'name': '编码'},
        {'id': 'name', 'name': '藏名'},
        {'id': 'short_name', 'name': '简称'},
        {'id': 'store_pattern', 'name': '存储模式'},
        {'id': 'img_available', 'name': '图片是否就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'remark', 'name': '备注'}
    ]
    rules = [
        (v.not_empty, 'tripitaka_code', 'name'),
        (v.is_tripitaka, 'tripitaka_code'),
    ]
    primary = 'tripitaka_code'

    page_title = '藏数据管理'
    search_tips = '请搜索藏经名称和编码'
    search_fields = ['name', 'tripitaka_code']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]


class Sutra(Model):
    collection = 'sutra'
    fields = [
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'sutra_name', 'name': '经名'},
        {'id': 'due_reel_count', 'name': '应存卷数', 'type': 'int'},
        {'id': 'existed_reel_count', 'name': '实存卷数', 'type': 'int'},
        {'id': 'author', 'name': '作译者'},
        {'id': 'trans_time', 'name': '翻译时间'},
        {'id': 'start_volume', 'name': '起始册'},
        {'id': 'start_page', 'name': '起始页', 'type': 'int'},
        {'id': 'end_volume', 'name': '终止册'},
        {'id': 'end_page', 'name': '终止页', 'type': 'int'},
        {'id': 'remark', 'name': '备注'}
    ]
    rules = [
        (v.not_empty, 'sutra_code', 'sutra_name'),
        (v.is_digit, 'due_reel_count', 'existed_reel_count', 'start_page', 'end_page'),
        (v.is_sutra, 'sutra_code')
    ]
    primary = 'sutra_code'

    page_title = '经数据管理'
    search_tips = '请搜索统一经编码、经编码、经名'
    search_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]


class Reel(Model):
    collection = 'reel'
    fields = [
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'sutra_name', 'name': '经名'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'reel_no', 'name': '卷序号', 'type': 'int'},
        {'id': 'start_volume', 'name': '起始册'},
        {'id': 'start_page', 'name': '起始页', 'type': 'int'},
        {'id': 'end_volume', 'name': '终止册'},
        {'id': 'end_page', 'name': '终止页', 'type': 'int'},
        {'id': 'remark', 'name': '备注'}
    ]
    rules = [
        (v.not_empty, 'sutra_code'),
        (v.is_digit, 'reel_no', 'start_page', 'end_page'),
        (v.is_sutra, 'sutra_code'),
        (v.is_reel, 'reel_code'),
    ]
    primary = 'reel_code'

    page_title = '卷数据管理'
    search_tips = '请搜索统一经编码、经编码、经名和卷编码'
    search_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]

    @classmethod
    def ignore_existed_check(cls, doc):
        # 卷序号为0时不做重复检查
        return str(doc.get('reel_no')) == '0'


class Volume(Model):
    collection = 'volume'
    fields = [
        {'id': 'tripitaka_code', 'name': '藏编码'},
        {'id': 'volume_code', 'name': '册编码'},
        {'id': 'envelop_no', 'name': '函序号'},
        {'id': 'volume_no', 'name': '册序号', 'type': 'int'},
        {'id': 'content_page_count', 'name': '正文页数'},
        {'id': 'content_pages', 'name': '正文页', 'input_type': 'textarea'},
        {'id': 'front_cover_pages', 'name': '封面页', 'input_type': 'textarea'},
        {'id': 'back_cover_pages', 'name': '封底页', 'input_type': 'textarea'},
        {'id': 'remark', 'name': '备注'},
    ]
    rules = [
        (v.not_empty, 'volume_code', 'tripitaka_code', 'volume_no'),
        (v.is_tripitaka, 'tripitaka_code'),
        (v.is_volume, 'volume_code'),
        (v.is_digit, 'volume_no'),
    ]
    primary = 'volume_code'

    page_title = '册数据管理'
    search_tips = '请搜索册编码'
    search_fields = ['volume_code']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields if f['id'] not in
                    ['content_pages', 'front_cover_pages', 'back_cover_pages']]
    info_fields = [f['id'] for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]

    @classmethod
    def pack_doc(cls, doc):
        doc = super().pack_doc(doc)
        if doc.get('content_pages') and isinstance(doc['content_pages'], str):
            content_pages = re.sub(r'[\[\]\"\'\s]', '', doc['content_pages']).split(',')
            content_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['content_pages'] = content_pages
        doc['content_page_count'] = len(doc.get('content_pages') or [])
        if doc.get('front_cover_pages') and isinstance(doc['front_cover_pages'], str):
            front_cover_pages = re.sub(r'[\[\]\"\'\s]', '', doc['front_cover_pages']).split(',')
            front_cover_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['front_cover_pages'] = front_cover_pages
        if doc.get('back_cover_pages') and isinstance(doc['back_cover_pages'], str):
            back_cover_pages = re.sub(r'[\[\]\"\'\s]', '', doc['back_cover_pages']).split(',')
            back_cover_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['back_cover_pages'] = back_cover_pages
        return doc


class Page(Model):
    collection = 'page'
    fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'width', 'name': '宽度'},
        {'id': 'height', 'name': '高度'},
        {'id': 'source', 'name': '批次'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'img_path', 'name': '图片路径'},
        {'id': 'img_cloud_path', 'name': '云图路径'},
        {'id': 'page_code', 'name': '对齐编码'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'blocks', 'name': '栏框数据'},
        {'id': 'columns', 'name': '列框数据'},
        {'id': 'chars', 'name': '字框数据'},
        {'id': 'ocr', 'name': '字框OCR'},
        {'id': 'ocr_col', 'name': '列框OCR'},
        {'id': 'text', 'name': '审定文本'},
        {'id': 'txt_html', 'name': '文本HTML'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'chars_col', 'name': '用户提交字序'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'lock.box', 'name': '切分锁'},
        {'id': 'lock.text', 'name': '文本锁'},
        {'id': 'level.box', 'name': '切分等级'},
        {'id': 'level.text', 'name': '文本等级'},
        {'id': 'remark.box', 'name': '切分备注'},
        {'id': 'remark.text', 'name': '文本备注'},
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
    layouts = ['上下一栏', '上下两栏', '上下三栏', '左右两栏']  # 图片的版面结构
    search_tips = '请搜索页编码、分类、页面结构、统一经编码、卷编码'
    search_fields = ['name', 'source', 'layout', 'uni_sutra_code', 'reel_code']

    @classmethod
    def metadata(cls):
        return dict(name='', width='', height='', img_suffix='', img_path='', img_cloud_path='',
                    page_code='', sutra_code='', uni_sutra_code='', reel_code='',
                    reel_page_no='', lock={}, blocks=[], columns=[], chars=[],
                    ocr='', ocr_col='', text='', txt_html='')

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
        {'id': 'data_level', 'name': '数据等级'},
        {'id': 'has_img', 'name': '是否已有字图'},
        {'id': 'img_need_updated', 'name': '是否需要更新字图'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'column', 'name': '所属列'},
        {'id': 'ocr_txt', 'name': 'OCR文字'},
        {'id': 'alternatives', 'name': 'OCR候选'},
        {'id': 'txt', 'name': '原字'},
        {'id': 'normal_txt', 'name': '正字'},
        {'id': 'txt_type', 'name': '类型'},
        {'id': 'txt_logs', 'name': '校对历史'},
        {'id': 'box_logs', 'name': '校对历史'},
        {'id': 'remark', 'name': '备注'},
    ]
    rules = [
        (v.is_page, 'page_name'),
    ]
    primary = 'id'

    txt_types = {'Z': '正字', 'Y': '广义异体字', 'X': '狭义异体字', 'M': '模糊字', 'N': '不确定', '*': '不认识'}
    edit_types = {'char_edit': '单字校对', 'cluster_proof': '聚类校对', 'cluster_review': '聚类审定'}
    # search_fields在这里定义，这样find_by_page时q参数才会起作用
    search_tips = '请搜索字编码、分类、文字'
    search_fields = ['name', 'source', 'ocr', 'txt', 'txt_normal']

    @classmethod
    def get_char_search_condition(cls, request_query):
        def c2int(c):
            return int(float(c) * 1000)

        condition, params = dict(), dict()
        for field in ['ocr_txt', 'txt', 'txt_type']:
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
