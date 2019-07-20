#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 如是藏经、实体藏经
@time: 2019/3/13
"""

from controller.base import BaseHandler


class RsTripitakaHandler(BaseHandler):
    URL = '/tripitaka/rs'

    def get(self):
        """ 如是藏经 """
        self.render('tripitaka_rs.html')


class CbetaHandler(BaseHandler):
    URL = '/cbeta'

    def get(self):
        """ CBETA """
        self.render('tripitaka_cbeta.html')


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka'

    def get(self):
        """ 藏经列表 """
        self.render('tripitaka_list.html')


class TripitakaHandler(BaseHandler):
    URL = '/tripitaka/@tripitaka_id'

    def get(self):
        """ 单个实体藏经 """
        self.render('tripitaka.html')
