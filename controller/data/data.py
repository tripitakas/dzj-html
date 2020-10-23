#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from functools import cmp_to_key
from controller.model import Model
from controller import helper as h
from controller import validate as v
from controller import errors


class Tripitaka(Model):
    collection = 'tripitaka'
    fields = [
        {'id': 'tripitaka_code', 'name': '编码'},
        {'id': 'name', 'name': '藏名'},
        {'id': 'short_name', 'name': '简称'},
        {'id': 'store_pattern', 'name': '存储模式'},
        {'id': 'first_page', 'name': '第一页'},
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
    info_fields = [f['id'] for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]

    @classmethod
    def get_need_fields(cls):
        return ['tripitaka_code', 'name', 'store_pattern']


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
    search_tips = '请搜索统一经编码、经编码、经名、起始册'
    search_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'start_volume']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    info_fields = [f['id'] for f in fields]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]

    @classmethod
    def get_need_fields(cls):
        return ['sutra_code', 'sutra_name', 'start_volume', 'start_page', 'end_volume', 'end_page']

    @classmethod
    def pack_doc(cls, doc, self=None):
        doc = super().pack_doc(doc)
        if re.match(r'\d+', doc.get('start_volume', '').strip()):
            doc['start_volume'] = '%s_%s' % (doc['sutra_code'][:2], doc['start_volume'].strip())
        if re.match(r'\d+', doc.get('end_volume', '').strip()):
            doc['end_volume'] = '%s_%s' % (doc['sutra_code'][:2], doc['end_volume'].strip())
        return doc


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
    search_tips = '请搜索统一经编码、经编码、经名、卷编码和起始册'
    search_fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'reel_code', 'start_volume']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields]
    info_fields = [f['id'] for f in fields]
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
        (v.not_empty, 'volume_code'),
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
    def get_need_fields(cls):
        # 设置必须字段，新增数据或批量上传时使用
        return ['volume_code']

    @classmethod
    def pack_doc(cls, doc, self=None):
        doc = super().pack_doc(doc)
        if not doc.get('tripitaka_code'):
            doc['tripitaka_code'] = doc['volume_code'].split('_')[0]
        if not doc.get('volume_no'):
            doc['volume_no'] = doc['volume_code'].split('_')[-1]
        if doc.get('content_pages') and isinstance(doc['content_pages'], str):
            content_pages = re.sub(r'[\[\]\"\'\s]', '', doc['content_pages']).split(',')
            content_pages.sort(key=cmp_to_key(h.cmp_page_code))
            doc['content_pages'] = content_pages
        doc['content_page_count'] = doc.get('content_page_count') or len(doc.get('content_pages') or [])
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
        {'id': 'uid', 'name': '编码'},
        {'id': 'txt', 'name': '异体字'},
        {'id': 'img_name', 'name': '异体字图'},
        {'id': 'normal_txt', 'name': '所属正字'},
        {'id': 'remark', 'name': '备注'},
        {'id': 'create_user_id', 'name': '创建人id'},
        {'id': 'create_by', 'name': '创建人'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
    ]
    rules = [
        (v.not_empty, 'normal_txt'),
    ]
    primary = '_id'

    search_tips = '请搜异体字、异体字图、正字及备注'
    search_fields = ['txt', 'img_name', 'normal_txt', 'remark']

    @classmethod
    def pack_doc(cls, doc, self=None):
        if doc.get('_id'):  # 更新
            doc['updated_time'] = datetime.now()
        else:  # 新增
            # 如果不是汉字，则转为图片字
            if doc.get('txt') and not re.match(r'^[^\x00-\xff]$', doc['txt']):
                doc['img_name'] = doc['txt'].strip()
                doc.pop('txt', 0)
            cond = {'img_name': doc['img_name']} if doc.get('img_name') else {'txt': doc['txt']}
            r = self.db.variant.find_one(cond)
            if r:
                return self.send_error_response(errors.variant_exist)
            if doc.get('img_name'):  # 如果是图片，则进行编码
                v_max = self.db.variant.find_one({'uid': {'$ne': None}}, sort=[('uid', -1)])
                doc['uid'] = int(v_max['uid']) + 1 if v_max else 1
                if self.db.char.find_one({'txt': 'Y%s' % doc['uid']}):
                    return self.send_error_response(errors.variant_exist, message='编号已错乱，请联系管理员！')
            doc['create_by'] = self.username
            doc['create_time'] = datetime.now()
            doc['create_user_id'] = self.user_id
        if doc.get('uid'):
            doc['uid'] = int(doc['uid'])
        if doc.get('txt'):
            doc['txt'] = doc['txt'].strip()
        if doc.get('normal_txt'):
            nt = doc['normal_txt']
            variant = self.db.variant.find_one({'uid': int(nt.strip('Y'))} if 'Y' in nt else {'txt': nt})
            if variant:
                doc['normal_txt'] = variant.get('normal_txt')
        doc = super().pack_doc(doc)
        return doc

    @classmethod
    def get_variant_search_condition(cls, request_query):
        condition, params = dict(), dict()
        q = h.get_url_param('q', request_query)
        if q and cls.search_fields:
            condition['$or'] = [{k: {'$regex': q, '$options': '$i'}} for k in cls.search_fields]
        for field in ['uid']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: int(value.strip('Y'))})
        for field in ['txt', 'normal_txt']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        for field in ['img_name', 'remark']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
        return condition, params
