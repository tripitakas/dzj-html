#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import json
import controller.validate as v
from functools import cmp_to_key
from controller.model import Model
from controller.task.task import Task
from controller.helper import prop, cmp_page_code, get_url_param


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
            content_pages.sort(key=cmp_to_key(cmp_page_code))
            doc['content_pages'] = content_pages
        doc['content_page_count'] = len(doc.get('content_pages') or [])
        if doc.get('front_cover_pages') and isinstance(doc['front_cover_pages'], str):
            front_cover_pages = re.sub(r'[\[\]\"\'\s]', '', doc['front_cover_pages']).split(',')
            front_cover_pages.sort(key=cmp_to_key(cmp_page_code))
            doc['front_cover_pages'] = front_cover_pages
        if doc.get('back_cover_pages') and isinstance(doc['back_cover_pages'], str):
            back_cover_pages = re.sub(r'[\[\]\"\'\s]', '', doc['back_cover_pages']).split(',')
            back_cover_pages.sort(key=cmp_to_key(cmp_page_code))
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
        {'id': 'box_ready', 'name': '切分已就绪'},
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
    def name2pagecode(cls, page_name):
        """ 把page的name转换为page_code，如GL_1_1_1转换为GL000100010001，即补齐为4位数字"""
        return ''.join([n.zfill(4) for n in page_name.split('_')]).lstrip('0')

    @classmethod
    def insert_many(cls, db, file_stream=None, layout=None, source=None):
        """ 插入新页面
        :param db 数据库连接
        :param file_stream 已打开的文件流。
        :param layout 页面的版面结构。
        :param source 页面分类
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
            page['source'] = source
            page['page_code'] = cls.name2pagecode(s[0])
            page['img_suffix'] = name2suffix.get(page_name)
            pages.append(page)
        if pages:
            r = db.page.insert_many(pages)
        message = '导入page，总共%s条记录，插入%s条，%s条旧数据。' % (len(page_names), len(pages), len(existed_pages))
        print(message)
        return dict(status='success', message=message, inserted_ids=r.inserted_ids if pages else [])

    @staticmethod
    def get_page_search_condition(request_query):
        condition, params = dict(), dict()
        for field in ['name', 'source', 'remark-box', 'remark-text']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field.replace('-', '.'): {'$regex': value, '$options': '$i'}})
        for field in ['level-box', 'level-text']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                m = re.search(r'([><=]?)(\d+)', value)
                if m:
                    op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m.group(1))
                    condition.update({field.replace('_', '.'): {op: value} if op else value})
        for field in ['cut_proof', 'cut_review', 'text_proof_1', 'text_proof_1', 'text_proof_3', 'text_review']:
            value = get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({'tasks.' + field: None if value == 'un_published' else value})
        value = get_url_param('txt', request_query)
        if value:
            params[field] = value
            condition.update({'$or': [{k: {'$regex': value}} for k in ['ocr', 'ocr_col', 'text']]})
        return condition, params

    @staticmethod
    def format_value(value, key=None):
        """ 格式化page表的字段输出"""
        if key == 'tasks':
            value = value or {}
            tasks = ['%s/%s' % (Task.get_task_name(k), Task.get_status_name(v)) for k, v in value.items()]
            value = '<br/>'.join(tasks)
        elif key in ['lock-box', 'lock-text']:
            if prop(value, 'is_temp') is not None:
                value = '临时锁<a>解锁</a>' if prop(value, 'is_temp') else '任务锁'
        elif key in ['cut-edit']:
            value = '修改'
        else:
            value = Task.format_value(value, key)
        return value
