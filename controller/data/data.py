#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from controller.data.cbeta import find
from controller.base import BaseHandler


class DataTripitakaHandler(BaseHandler):
    URL = '/data/tripitaka'

    def get(self):
        """ 数据管理-实体藏 """
        self.render('data_tripitaka.html')


class DataEnvelopHandler(BaseHandler):
    URL = '/data/envelop'

    def get(self):
        """ 数据管理-实体函 """
        self.render('data_envelop.html')


class DataVolumeHandler(BaseHandler):
    URL = '/data/volume'

    def get(self):
        """ 数据管理-实体册 """
        self.render('data_volume.html')


class DataSutraHandler(BaseHandler):
    URL = '/data/sutra'

    def get(self):
        """ 数据管理-实体经 """
        self.render('data_sutra.html')


class DataReelHandler(BaseHandler):
    URL = '/data/reel'

    def get(self):
        """ 数据管理-实体卷 """
        self.render('data_reel.html')


class DataPageHandler(BaseHandler):
    URL = '/data/page'

    def get(self):
        """ 数据管理-实体页 """
        self.render('data_page.html')


class DataSearchCbetaHandler(BaseHandler):
    URL = '/data/search_cbeta'

    def get(self):
        """ 检索cbeta库 """
        q = self.get_query_argument('q', '').strip()
        matches = find(q)
        for m in matches:
            regex = '[^\u2000-\u2FFFF]'     # 非汉字的其它字符
            highlights = {
                re.sub('</?kw>', '', v): re.sub('</kw><kw>', '', re.sub('</kw>(%s)<kw>' % regex, r'\g<1>', v))
                for v in m['highlight']['rows']
            }
            hits = [highlights[r] if r in highlights else r for r in m['_source']['rows']]
            m['hits'] = ''.join(hits)
        self.render('data_search_cbeta.html', q=q, matches=matches)
