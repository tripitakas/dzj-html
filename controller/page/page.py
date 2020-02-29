#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 页面工具
@time: 2019/6/3
"""
import re
import json
from .tool.box import Box
from controller.model import Model
from controller import validate as v
from controller.task.task import Task
from controller.helper import get_url_param, prop


class Page(Model, Box):
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
            page['page_code'] = cls.name2code(s[0])
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
        else:
            value = Task.format_value(value, key)
        return value

    @staticmethod
    def name2code(name):
        """ 把带_的name转换为用0填充、补齐的code，如GL_1_1_1转换为GL000100010001，即补齐为4位数字"""
        return ''.join([n.zfill(4) for n in name.split('_')]).lstrip('0')

    @staticmethod
    def cmp_page_code(a, b):
        """ 比较图片名称大小"""
        al, bl = a.split('_'), b.split('_')
        if len(al) != len(bl):
            return len(al) - len(bl)
        for i in range(len(al)):
            length = max(len(al[i]), len(bl[i]))
            ai, bi = al[i].zfill(length), bl[i].zfill(length)
            if ai != bi:
                return 1 if ai > bi else -1
        return 0
