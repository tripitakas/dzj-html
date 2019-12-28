#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from functools import cmp_to_key
from bson.objectid import ObjectId
import controller.errors as e
from controller.base import BaseHandler
from controller.helper import cmp_page_code
from controller.task.base import TaskHandler
from controller.data.data import Tripitaka, Volume, Sutra, Reel, Page


class TripitakaHandler(BaseHandler):
    URL = '/page/@page_code'

    def get(self, page_code='GL'):
        """ 藏经阅读 """
        try:
            m = re.match(r'^([A-Z]{1,2})([fb0-9_]*)?$', page_code)
            if not m:
                return self.send_error_response(e.page_code_error)
            tripitaka_code = m.group(1)
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': tripitaka_code})
            if not tripitaka:
                return self.send_error_response(e.no_object, message='藏经%s不存在' % tripitaka_code)
            elif tripitaka.get('img_available') == '否':
                return self.send_error_response(e.img_unavailable)

            # 根据存储模式补齐page_code
            name_slice = page_code.split('_')
            store_pattern = tripitaka.get('store_pattern')
            gap = len(store_pattern.split('_')) - len(name_slice)
            for i in range(gap):
                name_slice.append('1')
            page_code = '_'.join(name_slice)

            # 获取当前册信息
            cur_volume = self.db.volume.find_one({'volume_code': '_'.join(name_slice[:-1])})
            if not cur_volume:
                query = self.db.volume.find({'volume_code': {'$regex': '_'.join(name_slice[:-2]) + '_'}})
                r = list(query.sort('volume_no', 1).limit(1))
                cur_volume = r and r[0] or {}

            # 生成册导航信息
            nav = dict(cur_volume=cur_volume.get('volume_code'), cur_page=page_code)
            content_pages = cur_volume.get('content_pages')
            if content_pages:
                content_pages.sort(key=cmp_to_key(cmp_page_code))
                first, last = content_pages[0], content_pages[-1]
                cur_page = first if gap else page_code
                name_slice = cur_page.split('_')
                next = '%s_%s' % ('_'.join(name_slice[:-1]), int(name_slice[-1]) + 1)
                prev = '%s_%s' % ('_'.join(name_slice[:-1]), int(name_slice[-1]) - 1)
                nav.update(dict(cur_page=cur_page, first=first, last=last, prev=prev, next=next))

            # 获取图片路径及文本数据
            page = self.db.page.find_one({'name': nav.get('cur_page')})
            page_text = (page.get('text') or page.get('ocr') or page.get('ocr_col')) if page else ''
            img_url = self.get_img(page or dict(name=nav.get('cur_page')))

            self.render('tripitaka.html', tripitaka=tripitaka, tripitaka_code=tripitaka_code, nav=nav,
                        img_url=img_url, page_text=page_text, page=page)

        except Exception as error:
            return self.send_db_error(error)


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka/list'

    def get(self):
        """ 藏经列表 """
        fields = {'tripitaka_code': 1, 'name': 1, 'cover_img': 1, '_id': 0}
        tripitakas = list(self.db.tripitaka.find({'img_available': '是'}, fields))

        self.render('tripitaka_list.html', tripitakas=tripitakas, get_img=self.get_img)


class DataListHandler(BaseHandler):
    URL = '/data/(tripitaka|sutra|reel|volume)'

    def get(self, metadata):
        """ 数据管理"""
        try:
            model = eval(metadata.capitalize())
            docs, pager, q, order = model.find_by_page(self)
            kwargs = model.get_page_params()
            template_url = '/static/template/%s-sample.csv' % metadata
            kwargs['operations'] = [
                {'operation': 'btn-add', 'label': '新增记录'},
                {'operation': 'bat-remove', 'label': '批量删除'},
                {'operation': 'bat-upload', 'label': '批量上传', 'data-target': 'uploadModal'},
                {'operation': 'download-template', 'label': '下载模板', 'url': template_url},
            ]
            self.render('data_list.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class DataPageViewHandler(BaseHandler, Page):
    URL = '/data/page/@page_id'

    def get(self, page_id):
        """ 查看页数据"""
        try:
            page = self.db.page.find_one({'_id': ObjectId(page_id)})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面')

            fields = ['name', 'width', 'height', 'source', 'layout', 'img_cloud_path', 'page_code',
                      'uni_sutra_code', 'sutra_code', 'reel_code']
            metadata = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            fields = ['lock.box', 'lock.text', 'level.box', 'level.text']
            data_lock = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            fields = ['ocr', 'ocr_col', 'text']
            page_txt = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            fields = ['blocks', 'columns', 'chars']
            page_box = {k: self.prop(page, k) for k in fields if self.prop(page, k)}
            page_tasks = self.prop(page, 'tasks')

            self.render('data_page_view.html', metadata=metadata, data_lock=data_lock, page_txt=page_txt,
                        page_box=page_box, page_tasks=page_tasks, page=page,
                        Th=TaskHandler)

        except Exception as error:
            return self.send_db_error(error)


class DataPageHandler(TaskHandler):
    URL = '/data/page'

    task_statuses = {
        '': '', 'un_published': '未发布', 'opened': '已发布未领取', 'pending': '等待前置任务',
        'picked': '进行中', 'returned': '已退回', 'finished': '已完成',
    }

    @staticmethod
    def get_condition(self):
        condition, params = dict(), dict()
        for field in ['name', 'source', 'layout', 'box_ready']:
            value = self.get_query_argument(field, '')
            if value:
                params[field] = value
                condition.update({field: {'$regex': value, '$options': '$i'}})
        for field in ['level_box', 'level_text']:
            value = self.get_query_argument(field, '')
            m = re.search(r'([><=]+)(\d+)', value)
            if m:
                params[field] = m.group(0)
                op = {'>': '$gt', '<': '$lt', '>=': '$gte', '<=': '$lte'}.get(m.group(1))
                condition.update({field.replace('_', '.'): {op: value} if op else value})
        for field in ['cut_proof', 'cut_review', 'text_proof_1', 'text_proof_1', 'text_proof_3', 'text_review']:
            value = self.get_query_argument(field, '')
            if value:
                params[field] = value
                condition.update({'tasks.' + field: None if value == 'un_published' else value})
        return condition, params

    def get(self):
        """ 页数据管理"""
        try:
            model = Page
            condition, params = self.get_condition(self)
            docs, pager, q, order = model.find_by_page(self, condition=condition)
            kwargs = model.get_page_params()
            self.render('data_page.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        task_statuses=self.task_statuses, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class DataPagePublishHandler(TaskHandler):
    URL = '/data/page/publish/(box|text)'

    def get(self, kind):
        """ 发布任务"""
        try:
            condition, params = DataPageHandler.get_condition(self)
            page = self.db.page.find_one(condition, sort=[('_id', 1)])
            if not page:
                self.send_error_response(e.no_object, message='没有找到任何页面。查询条件%s' % str(params))
            current = self.get_query_argument('current', '')
            if current:
                next = self.get_query_argument('next', '')
                if next:
                    condition['_id'] = {'$gt': ObjectId(current)}
                    page = self.db.page.find_one(condition, sort=[('_id', 1)])
                    if not page:
                        self.send_error_response(e.no_object, message='没有下一条记录。查询条件%s，当前记录%s' % (current, str(params)))
                else:
                    condition['_id'] = ObjectId(current)
                    page = self.db.page.find_one(condition, sort=[('_id', 1)])
                    if not page:
                        self.send_error_response(e.no_object, message='当前记录%s不符合查询条件%s' % (current, str(params)))

            self.render('data_publish_%s.html' % kind, page=page, img_url=self.get_img(page), params=params)

        except Exception as error:
            return self.send_db_error(error)
