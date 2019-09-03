#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR页面
@time: 2019/9/2
"""
from controller.base import BaseHandler


class RecognitionHandler(BaseHandler):
    URL = '/data/ocr'

    def get(self):
        """ 藏经OCR页面 """
        try:
            self.render('data_ocr.html')

        except Exception as e:
            return self.send_db_error(e, render=True)
