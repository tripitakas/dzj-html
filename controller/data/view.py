#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from bson import json_util
from functools import cmp_to_key
from controller import errors as e
from controller.task.task import Task
from controller.base import BaseHandler
from controller.page.tool import PageTool
from controller.helper import cmp_page_code
from controller.task.base import TaskHandler
from controller.data.data import Tripitaka, Volume, Sutra, Reel, Page


class TripitakaHandler(BaseHandler):
    URL = '/page/@page_prefix'

    def get(self, page_name='GL'):
        """ 藏经阅读 """
        try:
            m = re.match(r'^([A-Z]{1,2})([fb0-9_]*)?$', page_name)
            if not m:
                return self.send_error_response(e.page_code_error)
            tripitaka_code = m.group(1)
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': tripitaka_code})
            if not tripitaka:
                return self.send_error_response(e.no_object, message='藏经%s不存在' % tripitaka_code)
            elif tripitaka.get('img_available') == '否':
                return self.send_error_response(e.img_unavailable)

            # 根据存储模式补齐page_name
            name_slice = page_name.split('_')
            store_pattern = tripitaka.get('store_pattern')
            gap = len(store_pattern.split('_')) - len(name_slice)
            for i in range(gap):
                name_slice.append('1')
            page_name = '_'.join(name_slice)

            # 获取当前册信息
            cur_volume = self.db.volume.find_one({'volume_code': '_'.join(name_slice[:-1])})
            if not cur_volume:
                query = self.db.volume.find({'volume_code': {'$regex': '_'.join(name_slice[:-2]) + '_'}})
                r = list(query.sort('volume_no', 1).limit(1))
                cur_volume = r and r[0] or {}

            # 生成册导航信息
            nav = dict(cur_volume=cur_volume.get('volume_code'), cur_page=page_name)
            content_pages = cur_volume.get('content_pages')
            if content_pages:
                content_pages.sort(key=cmp_to_key(cmp_page_code))
                first, last = content_pages[0], content_pages[-1]
                cur_page = first if gap else page_name
                name_slice = cur_page.split('_')
                next = '%s_%s' % ('_'.join(name_slice[:-1]), int(name_slice[-1]) + 1)
                prev = '%s_%s' % ('_'.join(name_slice[:-1]), int(name_slice[-1]) - 1)
                nav.update(dict(cur_page=cur_page, first=first, last=last, prev=prev, next=next))

            # 获取图片路径及文本数据
            page = self.db.page.find_one({'name': nav.get('cur_page')})
            page_text = (page.get('text') or page.get('ocr') or page.get('ocr_col')) if page else ''
            img_url = self.get_img(page or dict(name=nav.get('cur_page')))

            self.render('com_tripitaka.html', tripitaka=tripitaka, tripitaka_code=tripitaka_code, nav=nav,
                        img_url=img_url, page_text=page_text, page=page)

        except Exception as error:
            return self.send_db_error(error)


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka/list'

    def get(self):
        """ 藏经列表 """
        fields = {'tripitaka_code': 1, 'name': 1, 'cover_img': 1, '_id': 0}
        tripitakas = list(self.db.tripitaka.find({'img_available': '是'}, fields))
        self.render('com_tripitaka_list.html', tripitakas=tripitakas, get_img=self.get_img)


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


class DataPageInfoHandler(BaseHandler):
    URL = '/data/page/info/@page_name'

    def get(self, page_name):
        """ 页面详情"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            fields = ['name', 'width', 'height', 'source', 'layout', 'img_cloud_path', 'page_code',
                      'uni_sutra_code', 'sutra_code', 'reel_code']
            metadata = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            fields = ['lock.box', 'lock.text', 'level.box', 'level.text']
            data_lock = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            fields = ['ocr', 'ocr_col', 'text']
            page_txt = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            fields = ['blocks', 'columns', 'chars', 'chars_col']
            page_box = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            page_tasks = self.prop(page, 'tasks') or {}

            self.render('data_page_info.html', metadata=metadata, data_lock=data_lock, page_txt=page_txt,
                        page_box=page_box, page_tasks=page_tasks, page=page, Task=Task, Page=Page)

        except Exception as error:
            return self.send_db_error(error)


class DataPageListHandler(BaseHandler, Page):
    URL = '/data/page'

    page_title = '页数据管理'
    search_tips = '请搜索页名称、分类、页面结构、统一经编码、卷编码'
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
        {'id': 'box_ready', 'name': '切分已就绪'},
        {'id': 'level-box', 'name': '切分等级'},
        {'id': 'level-text', 'name': '文本等级'},
        {'id': 'lock-box', 'name': '切分锁'},
        {'id': 'lock-text', 'name': '文本锁'},
        {'id': 'remark-box', 'name': '切分备注'},
        {'id': 'remark-text', 'name': '文字备注'},
    ]
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-duplicate', 'label': '查找重复'},
        {'operation': 'bat-source', 'label': '更新分类'},
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
    info_fields = ['name', 'source', 'box_ready', 'layout', 'level-box', 'level-text', 'remark-box', 'remark-text']
    hide_fields = ['img_cloud_path', 'uni_sutra_code', 'sutra_code', 'reel_code', 'box_ready',
                   'lock-box', 'lock-text', 'level-box', 'level-text']
    update_fields = [
        {'id': 'name', 'name': '页编码', 'readonly': True},
        {'id': 'source', 'name': '分类'},
        {'id': 'box_ready', 'name': '切分已就绪', 'input_type': 'radio', 'options': ['是', '否']},
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
            p = {f: 0 for f in ['chars', 'columns', 'blocks', 'ocr', 'ocr_col', 'text', 'txt_html', 'char_ocr']}
            docs, pager, q, order = self.find_by_page(self, condition, default_order='page_code', projection=p)
            self.render('data_page_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, Th=TaskHandler,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class DataPageViewHandler(BaseHandler, Page):
    URL = '/data/page/@page_name'

    def get(self, page_name):
        """ 浏览页面数据"""
        edit_fields = [
            {'id': 'name', 'name': '页编码', 'readonly': True},
            {'id': 'box_ready', 'name': '切分已就绪', 'input_type': 'radio', 'options': ['是', '否']},
            {'id': 'layout', 'name': '图片结构', 'input_type': 'radio', 'options': self.layouts},
            {'id': 'source', 'name': '分类'},
            {'id': 'level-box', 'name': '切分等级'},
            {'id': 'level-text', 'name': '文本等级'},
        ]

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            condition = self.get_page_search_condition(self.request.query)[0]
            to = self.get_query_argument('to', '')
            if to == 'next':
                condition['page_code'] = {'$gt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', 1)])
            elif to == 'prev':
                condition['page_code'] = {'$lt': page['page_code']}
                page = self.db.page.find_one(condition, sort=[('page_code', -1)])
            if not page:
                message = '没有找到页面%s的%s' % (page_name, '上一页' if to == 'prev' else '下一页')
                return self.send_error_response(e.no_object, message=message)

            chars_col = PageTool.get_chars_col(page['chars'])
            labels = dict(text='审定文本', ocr='字框OCR', ocr_col='列框OCR')
            texts = [(f, page.get(f), labels.get(f)) for f in ['ocr', 'ocr_col', 'text'] if page.get(f)]
            info = {f['id']: self.prop(page, f['id'].replace('-', '.'), '') for f in edit_fields}
            btn_config = json_util.loads(self.get_secure_cookie('data_page_button') or '{}')
            self.render('data_page.html', page=page, chars_col=chars_col, btn_config=btn_config,
                        texts=texts, Th=TaskHandler, info=info, edit_fields=edit_fields,
                        img_url=self.get_img(page))

        except Exception as error:
            return self.send_db_error(error)
