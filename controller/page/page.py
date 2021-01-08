#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import json
from controller.model import Model
from controller import helper as h
from controller import validate as v


class Page(Model):
    primary = 'name'
    collection = 'page'
    layouts = ['上下一栏', '上下两栏', '上下三栏', '左右两栏']  # 图片的版面结构
    fields = {
        'name': {'name': '页编码'},
        'width': {'name': '宽度'},
        'height': {'name': '高度'},
        'source': {'name': '分类'},
        'layout': {'name': '页面结构', 'input_type': 'radio', 'options': layouts},
        'page_code': {'name': '对齐编码'},
        'book_page': {'name': '原书页码'},
        'uni_sutra_code': {'name': '统一经编码'},
        'sutra_code': {'name': '经编码'},
        'reel_code': {'name': '卷编码'},
        'blocks': {'name': '栏框数据'},
        'columns': {'name': '列框数据'},
        'chars': {'name': '字框数据'},
        'images': {'name': '图框数据'},
        'ocr': {'name': '字框OCR'},
        'ocr_col': {'name': '列框OCR'},
        'cmp_txt': {'name': '比对文本'},
        'txt': {'name': '审定文本'},
        'box_ready': {'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        'txt_match': {'name': '文本匹配'},
        'has_gen_chars': {'name': '是否已生成字数据'},
        'user_links': {'name': '用户序线'},
        'tasks_status': {'name': '任务状态'},
        'tasks_info': {'name': '任务信息'},
        'remark_box': {'name': '切分备注'},
        'remark_txt': {'name': '文本备注'},
        'op_text': {'name': '文本操作'},
    }
    rules = [(v.not_empty, 'name'), (v.is_page, 'name')]
    search_fields = ['name', 'source', 'layout', 'uni_sutra_code', 'reel_code']

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
