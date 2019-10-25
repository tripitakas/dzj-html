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
    URL = '/t/@page_code'

    def get(self, page_code='GL'):
        """ 藏经阅读 """
        try:
            m = re.match(r'^([A-Z]{1,2})([fb0-9_]*)?$', page_code)
            if not m:
                return self.send_error_response(errors.tptk_page_code_error, render=True)
            tripitaka_code = m.group(1)
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': tripitaka_code}) or {}
            if not tripitaka:
                return self.send_error_response(errors.tptk_not_existed, render=True)
            elif tripitaka.get('img_available') == '否':
                return self.send_error_response(errors.tptk_img_unavailable, render=True)

            # 根据存储模式补齐page_code
            store_pattern = tripitaka.get('store_pattern')
            name_slice = page_code.split('_')
            gap = len(store_pattern.split('_')) - len(name_slice)
            for i in range(gap):
                name_slice.append('1')

            # 获取当前册信息
            cur_volume = self.db.volume.find_one({'volume_code': '_'.join(name_slice[:-1])})
            if not cur_volume:
                cur_volume_regex = '_'.join(name_slice[:-2]) + '_'
                r = self.db.volume.find({'volume_code': {'$regex': cur_volume_regex}}).sort('volume_no', 1).limit(1)
                r = list(r)
                cur_volume = r and r[0] or {}

            # 生成册导航信息
            nav = dict(cur_volume=cur_volume.get('volume_code'), cur_page=page_code)
            content_pages = cur_volume.get('content_pages') or []
            if content_pages:
                content_pages.sort(key=cmp_to_key(cmp_page_code))
                first, last = content_pages[0], content_pages[-1]
                cur_page = first if gap else page_code
                pos = content_pages.index(cur_page)
                prev = content_pages[pos - 1 if pos > 1 else 0]
                next = content_pages[pos + 1 if pos < len(content_pages) - 1 else -1]
                nav.update(dict(cur_page=cur_page, first=first, last=last, prev=prev, next=next))

            # 获取图片路径
            page_code = nav.get('cur_page')
            img_url = self.get_img(page_code)

            # 检查文本数据
            page = self.db.page.find_one({'name': page_code})
            page_text = page and (page.get('text') or page.get('ocr')) or ''

            self.render('tripitaka.html', tripitaka=tripitaka, tripitaka_code=tripitaka_code,
                        nav=nav, img_url=img_url, page_text=page_text, page=page)

        except Exception as e:
            return self.send_db_error(e, render=True)


class TripitakaListHandler(BaseHandler):
    URL = '/tripitakas'

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
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            for v in volumes:
                for f in v:
                    if v[f] is None:
                        v[f] = ''
            self.render('data_volume.html', q=q, volumes=volumes, pager=pager)

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
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_sutra.html', q=q, sutras=sutras, pager=pager)

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
            condition = {"$or": [
                {"name": {'$regex': '.*%s.*' % q}},
                {"batch": {'$regex': '.*%s.*' % q}},
                {"sutra_id": {'$regex': '.*%s.*' % q}},
                {"reel_id": {'$regex': '.*%s.*' % q}},
            ]}
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.page.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            query = self.db.page.find(condition)
            pages = list(query.sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('data_page.html', q=q, pages=pages, pager=pager)

        except Exception as e:
            return self.send_db_error(e, render=True)