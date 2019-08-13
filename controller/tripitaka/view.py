#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 如是藏经、大藏经
@time: 2019/3/13
"""
import re
from functools import cmp_to_key
import controller.errors as errors
from controller.base import BaseHandler
from controller.helper import cmp_page_code


class TripitakaListHandler(BaseHandler):
    URL = '/tripitakas'

    def get(self):
        """ 藏经列表 """
        fields = {'tripitaka_code': 1, 'name': 1, 'cover_img': 1, '_id': 0}
        tripitakas = list(self.db.tripitaka.find({'img_available': '是'}, fields))

        self.render('tripitaka_list.html', tripitakas=tripitakas, get_img=self.get_img)


class RsTripitakaHandler(BaseHandler):
    URL = '/tripitaka/rs'

    def get(self):
        """ 如是藏经 """
        self.render('tripitaka_rs.html')


class TripitakaHandler(BaseHandler):
    URL = '/t/@page_code'

    def get(self, page_code='GL'):
        """ 藏经阅读 """
        try:
            m = re.match(r'^([A-Z]{1,2})([fb0-9_]*)?$', page_code)
            if not m:
                self.send_error_response(errors.tripitaka_page_code_error, render=True)
            tripitaka_code = m.group(1)
            tripitaka = self.db.tripitaka.find_one({'tripitaka_code': tripitaka_code}) or {}
            if not tripitaka:
                self.send_error_response(errors.tripitaka_not_existed, render=True)
            elif tripitaka.get('img_available') == '否':
                self.send_error_response(errors.tripitaka_img_unavailable, render=True)

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
                cur_volume = list(r)[0] if r else {}

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
            img_url = self.get_img(nav.get('cur_page'))

            # 检查文本数据
            page = self.db.page.find_one({'name': page_code})
            page_text = page and (page.get('text') or page.get('ocr')) or ''

            self.render('tripitaka.html', tripitaka=tripitaka, tripitaka_code=tripitaka_code,
                        nav=nav, img_url=img_url, page_text=page_text, page=page)

        except Exception as e:
            self.send_db_error(e, render=True)