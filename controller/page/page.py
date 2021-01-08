#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
from controller.model import Model
from controller import helper as h
from controller import validate as v


class Page(Model):
    collection = 'page'
    fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'width', 'name': '宽度'},
        {'id': 'height', 'name': '高度'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'page_code', 'name': '对齐编码'},
        {'id': 'book_page', 'name': '原书页码'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'blocks', 'name': '栏框数据'},
        {'id': 'columns', 'name': '列框数据'},
        {'id': 'chars', 'name': '字框数据'},
        {'id': 'images', 'name': '图框数据'},
        {'id': 'ocr', 'name': '字框OCR'},
        {'id': 'ocr_col', 'name': '列框OCR'},
        {'id': 'cmp_txt', 'name': '比对文本'},
        {'id': 'txt', 'name': '审定文本'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'txt_match', 'name': '文本匹配'},
        {'id': 'has_gen_chars', 'name': '是否已生成字数据'},
        {'id': 'user_links', 'name': '用户序线'},
        {'id': 'tasks_status', 'name': '任务状态'},
        {'id': 'tasks_info', 'name': '任务信息'},
        {'id': 'remark_box', 'name': '切分备注'},
        {'id': 'remark_txt', 'name': '文本备注'},
    ]
    rules = [
        (v.not_empty, 'name'),
        (v.is_page, 'name'),
    ]
    primary = 'name'
    search_tips = '请搜索页编码、分类、页面结构、统一经编码、卷编码'
    search_fields = ['name', 'source', 'layout', 'uni_sutra_code', 'reel_code']
    layouts = ['上下一栏', '上下两栏', '上下三栏', '左右两栏']  # 图片的版面结构

    @classmethod
    def metadata(cls):
        return dict(name='', width='', height='', source='', layout='', page_code='', sutra_code='',
                    uni_sutra_code='', reel_code='', reel_page_no='', blocks=[], columns=[], chars=[],
                    ocr='', ocr_col='', txt='')

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
        request_query = re.sub('[?&]?from=.*$', '', request_query)
        condition, params = dict(), dict()
        q = h.get_url_param('q', request_query)
        if q and cls.search_fields:
            m = re.match(r'["\'](.*)["\']', q)
            condition['$or'] = [{k: m.group(1) if m else {'$regex': q}} for k in cls.search_fields]
        for field in ['name', 'source', 'txt', 'remark_box', 'remark_txt']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                m = re.match(r'["\'](.*)["\']', value)
                condition.update({field: m.group(1) if m else {'$regex': value}})
        task_type = h.get_url_param('task_type', request_query)
        if task_type:
            params['task_type'] = task_type
        task_status = h.get_url_param('task_status', request_query)
        if task_status:
            params['task_status'] = task_status
        num = h.get_url_param('num', request_query) or 1
        params['num'] = num
        if task_type and task_status:
            condition.update({'tasks.%s.%s' % (task_type, num): None if task_status == 'un_published' else task_status})
        match_field = h.get_url_param('match_field', request_query)
        if match_field:
            params['match_field'] = match_field
        match_status = h.get_url_param('match_status', request_query)
        if match_status not in [None, '']:
            params['match_status'] = match_status
        if match_field and match_status not in [None, '']:
            condition.update({'txt_match.%s.status' % match_field: match_status})
        return condition, params
