#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import math
from controller.base import BaseHandler



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
                {"unified_sutra_code": {'$regex': '.*%s.*' % q}},
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
                {"unified_sutra_code": {'$regex': '.*%s.*' % q}},
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


class DataSearchCbetaHandler(BaseHandler):
    URL = '/data/cbeta/search'

    def get(self):
        """ 检索cbeta库 """
        self.render('data_cbeta_search.html')


class DataPunctuationHandler(BaseHandler):
    URL = '/data/punctuation'

    def get(self):
        """ 自动标点 """
        self.render('data_punctuation.html')
