#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from bson import json_util
from controller import errors as e
from controller.task.task import Task
from controller.base import BaseHandler
from controller.helper import align_code
from controller.page.tool.box import Box
from controller.data.data import Tripitaka, Volume, Sutra, Reel, Page, Char


class DataListHandler(BaseHandler):
    URL = '/data/(tripitaka|sutra|reel|volume)'

    def get(self, metadata):
        """ 数据管理"""
        try:
            model = eval(metadata.capitalize())
            kwargs = model.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            kwargs['img_operations'] = ['config']
            kwargs['operations'] = [
                {'operation': 'btn-add', 'label': '新增记录'},
                {'operation': 'bat-remove', 'label': '批量删除'},
                {'operation': 'bat-upload', 'label': '批量上传', 'data-target': 'uploadModal'},
                {'operation': 'download-template', 'label': '下载模板',
                 'url': '/static/template/%s-sample.csv' % metadata},
            ]
            docs, pager, q, order = model.find_by_page(self)
            self.render('data_list.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageListHandler(BaseHandler, Page):
    URL = '/data/page'

    # 列表相关参数
    page_title = '页数据管理'
    search_tips = '请搜索页编码、分类、页面结构、统一经编码、卷编码'
    search_fields = ['name', 'source', 'layout', 'uni_sutra_code', 'reel_code']
    table_fields = [
        {'id': 'name', 'name': '页编码'},
        {'id': 'source', 'name': '分类'},
        {'id': 'layout', 'name': '页面结构'},
        {'id': 'img_cloud_path', 'name': '云图路径'},
        {'id': 'uni_sutra_code', 'name': '统一经编码'},
        {'id': 'sutra_code', 'name': '经编码'},
        {'id': 'reel_code', 'name': '卷编码'},
        {'id': 'tasks', 'name': '任务'},
        {'id': 'box_ready', 'name': '切分就绪'},
        {'id': 'level-box', 'name': '切分等级'},
        {'id': 'level-text', 'name': '文本等级'},
        {'id': 'lock-box', 'name': '切分锁'},
        {'id': 'lock-text', 'name': '文本锁'},
        {'id': 'remark-box', 'name': '切分备注'},
        {'id': 'remark-text', 'name': '文字备注'},
    ]
    info_fields = [
        'name', 'source', 'box_ready', 'layout', 'level-box', 'level-text',
        'remark-box', 'remark-text'
    ]
    hide_fields = [
        'img_cloud_path', 'uni_sutra_code', 'sutra_code', 'reel_code', 'box_ready',
        'lock-box', 'lock-text', 'level-box', 'level-text'
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-export-char', 'label': '生成字表'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in Task.get_task_types('page').items()
        ]},
    ]
    actions = [
        {'action': 'btn-nav', 'label': '浏览'},
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-box', 'label': '字框'},
        {'action': 'btn-order', 'label': '字序'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    update_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'source', 'name': '分类'},
        {'id': 'box_ready', 'name': '切分就绪', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': Page.layouts},
        {'id': 'level-box', 'name': '切分等级'},
        {'id': 'level-text', 'name': '文本等级'},
        {'id': 'remark-box', 'name': '切分备注'},
        {'id': 'remark-text', 'name': '文本备注'},
    ]
    task_statuses = {
        '': '', 'un_published': '未发布', 'published': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }

    def get_duplicate_condition(self):
        pages = list(self.db.page.aggregate([
            {'$group': {'_id': '$name', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'name': {'$in': [p['_id'] for p in pages]}}
        params = {'duplicate': 'true'}
        return condition, params

    def get(self):
        """ 页数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']

            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = self.get_page_search_condition(self.request.query)
            fields = ['chars', 'columns', 'blocks', 'ocr', 'ocr_col', 'text', 'txt_html', 'char_ocr']
            docs, pager, q, order = self.find_by_page(self, condition, None, 'page_code', {f: 0 for f in fields})

            self.render('data_page_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, format_value=self.format_value,
                        Task=Task, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class PageInfoHandler(BaseHandler):
    URL = '/data/page/info/@page_name'

    def get(self, page_name):
        """ 页面详情"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            fields1 = ['lock.box', 'lock.text', 'level.box', 'level.text']
            data_lock = {k: self.prop(page, k) for k in fields1 if self.prop(page, k)}
            fields2 = ['ocr', 'ocr_col', 'text']
            page_txt = {k: self.prop(page, k) for k in fields2 if self.prop(page, k)}
            fields3 = ['blocks', 'columns', 'chars', 'chars_col']
            page_box = {k: self.prop(page, k) for k in fields3 if self.prop(page, k)}
            fields4 = list(set(page.keys()) - set(fields1 + fields2 + fields3))
            metadata = {k: self.prop(page, k) for k in fields4 if self.prop(page, k)}
            page_tasks = self.prop(page, 'tasks') or {}

            self.render('data_page_info.html', metadata=metadata, data_lock=data_lock, page_txt=page_txt,
                        page_box=page_box, page_tasks=page_tasks, page=page, Task=Task)

        except Exception as error:
            return self.send_db_error(error)


class CharListHandler(BaseHandler, Char):
    URL = '/data/char'

    page_title = '字数据管理'
    search_tips = '请搜索字编码、分类、文字'
    search_fields = ['id', 'source', 'ocr', 'txt']
    table_fields = [
        {'id': 'has_img', 'name': '字图'},
        {'id': 'id', 'name': 'id'},
        {'id': 'source', 'name': '分类'},
        {'id': 'column_cid', 'name': '所属列'},
        {'id': 'ocr', 'name': 'OCR文字'},
        {'id': 'options', 'name': 'OCR候选'},
        {'id': 'txt', 'name': '校对文字'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'cc', 'name': '置信度'},
        {'id': 'sc', 'name': '相似度'},
        {'id': 'pos', 'name': '坐标'},
        {'id': 'log', 'name': '校对记录'},
        {'id': 'remark', 'name': '备注'},
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
        {'operation': 'bat-gen-img', 'label': '生成字图'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
        {'operation': 'btn-browse', 'label': '浏览结果'},
        {'operation': 'btn-publish', 'label': '发布任务', 'groups': [
            {'operation': k, 'label': v} for k, v in Task.get_task_types('char').items()
        ]},
    ]
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    hide_fields = ['log', 'options']
    info_fields = ['has_img', 'source', 'txt', 'txt_type', 'remark']
    update_fields = [
        {'id': 'has_img', 'name': '已有字图', 'input_type': 'radio', 'options': ['是', '否']},
        {'id': 'source', 'name': '分　　类'},
        {'id': 'txt', 'name': '校对文字'},
        {'id': 'txt_type', 'name': '文字类型'},
        {'id': 'remark', 'name': '备　　注'},
    ]
    txt_types = {
        '': '', 'X': '狭义异体字', 'Y': '广义异体字', 'M': '模糊字',
        'N': '拿不准', '*': '不认识',
    }

    def get_duplicate_condition(self):
        chars = list(self.db.char.aggregate([
            {'$group': {'_id': '$id', 'count': {'$sum': 1}}},
            {'$match': {'count': {'$gte': 2}}},
        ]))
        condition = {'id': {'$in': [c['_id'] for c in chars]}}
        params = {'duplicate': 'true'}
        return condition, params

    def format_value(self, value, key=None, doc=None):
        """ 格式化page表的字段输出"""
        if key == 'pos':
            value = '/'.join([str(value.get(f)) for f in ['x', 'y', 'w', 'h']])
        if key == 'has_img' and value:
            value = r'<img class="char-img" src="%s"/>' % self.get_web_img(doc['id'], 'char')
        else:
            value = Task.format_value(value, key)
        return value

    def get(self):
        """ 字数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            if self.get_query_argument('duplicate', '') == 'true':
                condition, params = self.get_duplicate_condition()
            else:
                condition, params = self.get_char_search_condition(self.request.query)
            docs, pager, q, order = self.find_by_page(self, condition)
            self.render('data_char_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        Task=Task, txt_types=self.txt_types, format_value=self.format_value,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)