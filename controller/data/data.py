#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from functools import cmp_to_key
from controller.model import Model
from controller import helper as h
from controller import validate as v


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


class Variant(Model):
    collection = 'variant'
    fields = [
        {'id': 'variant_code', 'name': '编码'},
        {'id': 'txt', 'name': '异体字'},
        {'id': 'normal_txt', 'name': '所属正字'},
        {'id': 'img_code', 'name': '字图'},
        {'id': 'remark', 'name': '备注'}
    ]
    rules = [
        (v.not_empty, 'txt'),
    ]
    primary = 'txt'

    page_title = '异体字管理'
    search_tips = '请搜异体字、正字及编码'
    search_fields = ['txt', 'normal_txt', 'remark']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]