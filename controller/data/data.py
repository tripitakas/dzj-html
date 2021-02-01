#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from functools import cmp_to_key
from controller.model import Model
from controller import helper as h
from controller import validate as v


class Tripitaka(Model):
    collection = 'tripitaka'
    primary = 'tripitaka_code'
    fields = {
        'name': {'name': '藏名'},
        'short_name': {'name': '简称'},
        'tripitaka_code': {'name': '编码'},
        'store_pattern': {'name': '存储模式'},
        'first_page': {'name': '第一页'},
        'img_available': {'name': '图片是否就绪', 'input_type': 'radio', 'options': ['是', '否']},
        'remark': {'name': '备注'},
        'create_time': {'name': '创建时间'},
        'updated_time': {'name': '更新时间'},
    }
    rules = [
        (v.not_empty, 'tripitaka_code', 'name'),
        (v.is_tripitaka, 'tripitaka_code'),
    ]

    page_title = '藏数据管理'
    search_fields = ['name', 'tripitaka_code']
    table_fields = ['tripitaka_code', 'name', 'short_name', 'store_pattern', 'first_page', 'img_available', 'remark']
    update_fields = table_fields

    @classmethod
    def get_need_fields(cls):
        return ['tripitaka_code', 'name', 'store_pattern']


class Sutra(Model):
    collection = 'sutra'
    primary = 'sutra_code'
    fields = {
        'uni_sutra_code': {'name': '统一经编码'},
        'sutra_code': {'name': '经编码'},
        'sutra_name': {'name': '经名'},
        'author': {'name': '作译者'},
        'start_volume': {'name': '起始册'},
        'start_page': {'name': '起始页', 'type': 'int'},
        'end_volume': {'name': '终止册'},
        'end_page': {'name': '终止页', 'type': 'int'},
        'due_reel_count': {'name': '应存卷数', 'type': 'int'},
        'existed_reel_count': {'name': '实存卷数', 'type': 'int'},
        'category': {'name': '分类'},
        'thousand': {'name': '千字文'},
        'trans_time': {'name': '翻译时间'},
        'remark': {'name': '备注'},
        'create_time': {'name': '创建时间'},
        'updated_time': {'name': '更新时间'},
    }
    rules = [
        (v.not_empty, 'sutra_code', 'sutra_name'),
        (v.is_digit, 'due_reel_count', 'existed_reel_count', 'start_page', 'end_page'),
        (v.is_sutra, 'sutra_code')
    ]

    page_title = '经数据管理'
    search_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'author', 'category', 'start_volume']
    table_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'author', 'start_volume', 'start_page',
                    'end_volume', 'end_page', 'due_reel_count', 'existed_reel_count',
                    'category', 'thousand', 'trans_time', 'remark']
    update_fields = table_fields

    @classmethod
    def get_need_fields(cls):
        return ['sutra_code', 'sutra_name', 'start_volume', 'start_page', 'end_volume', 'end_page']

    @classmethod
    def pack_doc(cls, doc, self=None, exclude_none=False):
        doc = super().pack_doc(doc)
        if re.match(r'\d+', doc.get('start_volume', '').strip()):
            doc['start_volume'] = '%s_%s' % (doc['sutra_code'][:2], doc['start_volume'].strip())
        if re.match(r'\d+', doc.get('end_volume', '').strip()):
            doc['end_volume'] = '%s_%s' % (doc['sutra_code'][:2], doc['end_volume'].strip())
        return doc


class Reel(Model):
    collection = 'reel'
    primary = 'reel_code'
    fields = {
        'uni_sutra_code': {'name': '统一经编码'},
        'sutra_code': {'name': '经编码'},
        'sutra_name': {'name': '经名'},
        'reel_code': {'name': '卷编码'},
        'reel_no': {'name': '卷序号', 'type': 'int'},
        'start_volume': {'name': '起始册'},
        'start_page': {'name': '起始页', 'type': 'int'},
        'end_volume': {'name': '终止册'},
        'end_page': {'name': '终止页', 'type': 'int'},
        'remark': {'name': '备注'},
        'create_time': {'name': '创建时间'},
        'updated_time': {'name': '更新时间'},
    }
    rules = [
        (v.not_empty, 'sutra_code'),
        (v.is_digit, 'reel_no', 'start_page', 'end_page'),
        (v.is_sutra, 'sutra_code'),
        (v.is_reel, 'reel_code'),
    ]

    page_title = '卷数据管理'
    search_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'reel_code', 'start_volume']
    table_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'reel_code', 'reel_no',
                    'start_volume', 'start_page', 'end_volume', 'end_page', 'remark']
    update_fields = table_fields

    @classmethod
    def ignore_existed_check(cls, doc):
        return str(doc.get('reel_no')) == '0'  # 卷序号为0时不做重复检查


class Volume(Model):
    collection = 'volume'
    fields = {
        'tripitaka_code': {'name': '藏编码'},
        'volume_code': {'name': '册编码'},
        'category': {'name': '分类'},
        'envelop_no': {'name': '函序号'},
        'volume_no': {'name': '册序号', 'type': 'int'},
        'content_page_count': {'name': '正文页数'},
        'content_pages': {'name': '正文页', 'input_type': 'textarea'},
        'front_cover_pages': {'name': '封面页', 'input_type': 'textarea'},
        'back_cover_pages': {'name': '封底页', 'input_type': 'textarea'},
        'remark': {'name': '备注'},
        'create_time': {'name': '创建时间'},
        'updated_time': {'name': '更新时间'},
    }
    rules = [
        (v.not_empty, 'volume_code'),
        (v.is_tripitaka, 'tripitaka_code'),
        (v.is_volume, 'volume_code'),
        (v.is_digit, 'volume_no'),
    ]
    primary = 'volume_code'

    page_title = '册数据管理'
    search_fields = ['volume_code', 'category']
    table_fields = ['tripitaka_code', 'volume_code', 'category', 'envelop_no', 'volume_no',
                    'content_page_count', 'remark']
    update_fields = table_fields

    @classmethod
    def get_need_fields(cls):
        # 设置必须字段，新增数据或批量上传时使用
        return ['volume_code']

    @classmethod
    def pack_doc(cls, doc, self=None, exclude_none=False):
        reg = r'[\[\]\"\'\s]'
        doc = super().pack_doc(doc)
        if not doc.get('tripitaka_code'):
            doc['tripitaka_code'] = doc['volume_code'].split('_')[0]
        if not doc.get('volume_no'):
            doc['volume_no'] = doc['volume_code'].split('_')[-1]
        if doc.get('content_pages') and isinstance(doc['content_pages'], str):
            content_pages = re.sub(reg, '', doc['content_pages']).split(',')
            content_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['content_pages'] = content_pages
        doc['content_page_count'] = doc.get('content_page_count') or len(doc.get('content_pages') or [])
        if doc.get('front_cover_pages') and isinstance(doc['front_cover_pages'], str):
            front_cover_pages = re.sub(reg, '', doc['front_cover_pages']).split(',')
            front_cover_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['front_cover_pages'] = front_cover_pages
        if doc.get('back_cover_pages') and isinstance(doc['back_cover_pages'], str):
            back_cover_pages = re.sub(reg, '', doc['back_cover_pages']).split(',')
            back_cover_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['back_cover_pages'] = back_cover_pages
        return doc


class Variant(Model):
    primary = '_id'
    collection = 'variant'
    fields = {
        'uid': {'name': '序号'},
        'v_code': {'name': '编码'},
        'source': {'name': '分类'},
        'txt': {'name': '异体字'},
        'img_name': {'name': '异体字图'},
        'user_txt': {'name': '用户字头'},
        'nor_txt': {'name': '所属正字'},
        'remark': {'name': '备注'},
        'create_user_id': {'name': '创建人id'},
        'create_by': {'name': '创建人'},
        'create_time': {'name': '创建时间'},
        'updated_time': {'name': '更新时间'},
    }
    rules = [(v.not_both_empty, 'img_name', 'txt'), (v.not_both_empty, 'nor_txt', 'user_txt')]

    @classmethod
    def get_variant_search_condition(cls, request_query):
        condition, params = dict(), dict()
        q = h.get_url_param('q', request_query)
        if q and cls.search_fields:
            m = len(q) > 1 and q[0] == '='
            condition['$or'] = [{k: q[1:] if m else {'$regex': q}} for k in cls.search_fields]
        for field in ['txt', 'nor_txt']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        for field in ['v_code', 'img_name', 'source', 'remark']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value[1:] if len(value) > 1 and value[0] == '=' else {'$regex': value}})
        return condition, params
