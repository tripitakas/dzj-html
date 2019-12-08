#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
import math
from functools import cmp_to_key
import controller.errors as errors
from controller.base import BaseHandler
from controller.helper import cmp_page_code


class TripitakaHandler(BaseHandler):
    URL = '/page/@page_code'

    def get(self, page_code='GL'):
        """ 藏经阅读 """
        try:
            m = re.match(r'^([A-Z]{1,2})([fb0-9_]*)?$', page_code)
            if not m:
                return self.send_error_response(errors.tptk_page_code_error)
            tripitaka_code = m.group(1)
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': tripitaka_code})
            if not tripitaka:
                return self.send_error_response(errors.tptk_not_existed)
            elif tripitaka.get('img_available') == '否':
                return self.send_error_response(errors.tptk_img_unavailable)

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

        except Exception as e:
            return self.send_db_error(e, render=True)


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka/list'

    def get(self):
        """ 藏经列表 """
        fields = {'tripitaka_code': 1, 'name': 1, 'cover_img': 1, '_id': 0}
        tripitakas = list(self.db.tripitaka.find({'img_available': '是'}, fields))

        self.render('tripitaka_list.html', tripitakas=tripitakas, get_img=self.get_img)


class DataTripitakaHandler(BaseHandler):
    URL = '/data/tripitaka'

    def get(self):
        """ 数据管理-藏数据 """
        try:
            q = self.get_query_argument('q', '').upper()
            condition = {"$or": [
                {"tripitaka_code": {'$regex': '.*%s.*' % q}},
                {"name": {'$regex': '.*%s.*' % q}}
            ]}
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.tripitaka.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            query = self.db.tripitaka.find(condition)
            tripitakas = list(query.sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_tripitaka.html', q=q, tripitakas=tripitakas, pager=pager)

        except Exception as e:
            return self.send_db_error(e, render=True)


class DataVolumeHandler(BaseHandler):
    URL = '/data/volume'

    def get(self):
        """ 数据管理-册数据 """
        try:
            q = self.get_query_argument('q', '').upper()
            condition = {"$or": [
                {"volume_code": {'$regex': '.*%s.*' % q}}
            ]}
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.volume.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            query = self.db.volume.find(condition)
            volumes = list(query.sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            tripitakas = ['所有'] + self.db.volume.find().distinct('tripitaka_code')
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_volume.html', q=q, volumes=volumes, tripitakas=tripitakas, pager=pager)

        except Exception as e:
            return self.send_db_error(e, render=True)


class DataSutraHandler(BaseHandler):
    URL = '/data/sutra'

    def get(self):
        """ 数据管理-经数据 """
        try:
            q = self.get_query_argument('q', '').upper()
            condition = {"$or": [
                {"uni_sutra_code": {'$regex': '.*%s.*' % q}},
                {"sutra_code": {'$regex': '.*%s.*' % q}},
                {"sutra_name": {'$regex': '.*%s.*' % q}},
            ]}
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.sutra.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            query = self.db.sutra.find(condition)
            sutras = list(query.sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            tripitakas = ['所有'] + list(set(r[:2] for r in self.db.sutra.find().distinct('sutra_code')))
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_sutra.html', q=q, sutras=sutras, tripitakas=tripitakas, pager=pager)

        except Exception as e:
            return self.send_db_error(e, render=True)


class DataReelHandler(BaseHandler):
    URL = '/data/reel'

    def get(self):
        """ 数据管理-卷数据 """
        try:
            q = self.get_query_argument('q', '').upper()
            condition = {"$or": [
                {"uni_sutra_code": {'$regex': '.*%s.*' % q}},
                {"sutra_code": {'$regex': '.*%s.*' % q}},
                {"sutra_name": {'$regex': '.*%s.*' % q}},
            ]}
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.reel.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            query = self.db.reel.find(condition)
            reels = list(query.sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_reel.html', q=q, reels=reels, pager=pager)

        except Exception as e:
            return self.send_db_error(e, render=True)


class DataPageHandler(BaseHandler):
    URL = '/data/page'

    def get(self):
        """ 数据管理-页数据 """
        try:
            q = self.get_query_argument('q', '').upper()
            order = self.get_query_argument('order', '-_id')
            condition = {'$or': [
                {'name': {'$regex': '.*%s.*' % q}},
                {'uni_sutra_code': {'$regex': '.*%s.*' % q}},
                {'sutra_code': {'$regex': '.*%s.*' % q}},
                {'reel_code': {'$regex': '.*%s.*' % q}},
            ]}
            query = self.db.page.find(condition)
            if order:
                o, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
                query.sort(o, asc)
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.page.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            pages = list(query.skip((cur_page - 1) * page_size).limit(page_size))
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_page.html', q=q, pages=pages, pager=pager, order=order)

        except Exception as e:
            return self.send_db_error(e, render=True)
