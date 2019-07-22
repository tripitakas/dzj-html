#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from controller.base import BaseHandler
from controller.data.cbeta_search import find
from controller.data.variant import normalize


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
    URL = '/data/cbeta/search'

    def get(self):
        """ 检索cbeta库 """

        def merge_kw(txt):
            # 将<kw>一</kw>，<kw>二</kw>格式替换为<kw>一，二</kw>
            regex = r'[，、：；。？！“”‘’「」『』（）%&*◎—……]+'
            txt = re.sub('</kw>(%s)<kw>' % regex, lambda r: r.group(1), txt)
            # 合并相邻的关键字
            txt = re.sub('</kw><kw>', '', txt)
            return txt

        q = self.get_query_argument('q', '').strip()
        try:
            matches = find(q)
        except Exception as e:
            matches = [dict(hits=[str(e)])]
        for m in matches:
            try:
                highlights = {re.sub('</?kw>', '', v): merge_kw(v) for v in m['highlight']['normal']}
                hits = [highlights.get(normalize(r), r) for r in m['_source']['origin']]
                m['hits'] = hits  # ''.join(hits)
            except KeyError:
                m['hits'] = m.get('hits') or m['_source']['origin']

        self.render('data_cbeta_search.html', q=q, matches=matches)
