#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from functools import cmp_to_key
from controller import errors as e
from controller.base import BaseHandler
from controller.helper import cmp_page_code
from controller.page.base import PageHandler
from controller.data.data import Sutra, Volume, Reel


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka/list'

    def get(self):
        """藏经列表"""
        tripitakas = list(self.db.tripitaka.find({'img_available': '是'}))
        self.render('tptk_list.html', tripitakas=tripitakas)


class TripitakaPageHandler(PageHandler):
    URL = '/page/@page_prefix'

    @staticmethod
    def get_book_meta(page):
        if page.get('book_page'):
            v, p, b = page['book_page'].split('_')
            return '册%s，页%s，栏%s' % (v, p, b)

    @staticmethod
    def pad_name(page_name, level=3):
        """根据层次补齐page_name"""
        name_slice = page_name.split('_')
        gap = level - len(name_slice)
        for i in range(gap):
            name_slice.append('1')
        return '_'.join(name_slice)

    def get(self, page_name):
        """藏经阅读"""
        try:
            m = re.match(r'^([A-Z]{1,2})([fb0-9_]*)?$', page_name)
            if not m:
                return self.send_error_response(e.page_code_error)
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': m.group(1)})
            if not tripitaka:
                return self.send_error_response(e.no_object, message='藏经%s不存在' % m.group(1))

            # 获取当前页信息
            if len(page_name) == 2 and tripitaka.get('first_page'):
                page_name = tripitaka.get('first_page')
            assert tripitaka.get('store_pattern')
            level = len(tripitaka['store_pattern'].split('_'))
            page_name = self.pad_name(page_name, level)
            name_slice = page_name.split('_')
            cur_page = int(name_slice[-1])
            page = self.db.page.find_one({'name': page_name}) or dict(name=page_name)
            self.pack_boxes(page, log=False)
            page['img_url'] = self.get_web_img(page_name)
            txts = [(self.get_char_txt(page, 'adapt'), 'txt', '校对文本')] if page.get('chars') else []

            # 获取当前册信息
            volume_code = '_'.join(name_slice[:-1])
            volume = self.db.volume.find_one({'volume_code': volume_code})
            if not volume:
                cond = {'volume_code': {'$regex': '_'.join(name_slice[:-2]) + '_'}}
                volume = self.db.volume.find_one(cond, sort=[('volume_no', 1)])
            nav = dict(first=1, cur=cur_page, next=cur_page + 1, last=1, prev=cur_page - 1 if cur_page - 1 > 1 else 1)
            content_pages = volume and volume.get('content_pages')
            if content_pages:
                content_pages.sort(key=cmp_to_key(cmp_page_code))
                nav['last'] = int(content_pages[-1].split('_')[-1])
                if nav['next'] > nav['last']:
                    nav['next'] = nav['last']

            cid = self.get_query_argument('cid', '')
            book_meta = self.get_book_meta(page) or ''
            self.render(
                'tptk_page.html', tripitaka=tripitaka, page=page, volume_code=volume_code, txts=txts,
                tripitaka_code=name_slice[0], book_meta=book_meta, nav=nav, cid=cid,
            )

        except Exception as error:
            return self.send_db_error(error)


class TripitakaDataHandler(BaseHandler):
    URL = '/(sutra|reel|volume)/@tripitaka_code'

    @staticmethod
    def get_template_kwargs(model):
        kwargs = model.get_template_kwargs()
        kwargs['actions'] = []
        kwargs['search_tips'] = kwargs['search_tips'].replace('统一经编码、', '')
        hide_fields = ['envelop_no', 'volume_no', 'uni_sutra_code', 'trans_time', 'remark']
        kwargs['search_fields'] = [f for f in kwargs['search_fields'] if f not in hide_fields]
        kwargs['table_fields'] = [f for f in kwargs['table_fields'] if f['id'] not in hide_fields]
        return kwargs

    def get(self, collection, tripitaka_code):
        """前台基础数据检索"""
        try:
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': tripitaka_code})
            if not tripitaka:
                return self.send_error_response(e.no_object, message='藏经%s不存在' % tripitaka_code)

            model = eval(collection.capitalize())
            kwargs = self.get_template_kwargs(model)
            trans = dict(sutra='经', reel='卷', volume='册')
            title = '%s-%s目' % (tripitaka['name'], trans[collection])
            cond = {'%s_code' % collection: {'$regex': tripitaka_code}}
            docs, pager, q, order = model.find_by_page(self, cond, kwargs['search_fields'])
            self.render('tptk_data.html', collection=collection, tripitaka=tripitaka, tripitaka_code=tripitaka_code,
                        title=title, docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class TripitakaViewHandler(BaseHandler):
    URL = '/tripitaka/@page_prefix'

    def get(self, page_name='GL'):
        """藏经阅读"""
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
                nxt = '%s_%s' % ('_'.join(name_slice[:-1]), int(name_slice[-1]) + 1)
                prev = '%s_%s' % ('_'.join(name_slice[:-1]), int(name_slice[-1]) - 1)
                nav.update(dict(cur_page=cur_page, first=first, last=last, prev=prev, next=nxt))
            # 获取图片路径及文本数据
            page = self.db.page.find_one({'name': nav.get('cur_page')})
            page_text = (page.get('text') or page.get('ocr') or page.get('ocr_col')) if page else ''
            img_url = self.get_web_img(nav.get('cur_page'))

            self.render('tripitaka.html', tripitaka=tripitaka, tripitaka_code=tripitaka_code, nav=nav,
                        img_url=img_url, page_text=page_text, page=page)

        except Exception as error:
            return self.send_db_error(error)
