#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR页面
@time: 2019/9/2
"""
from controller.base import BaseHandler
from os import path
import json


class RecognitionHandler(BaseHandler):
    URL = '/data/ocr'

    def get(self):
        """ 藏经OCR页面 """
        try:
            json_file = path.join(self.application.BASE_DIR, 'static', 'imgs', '001_006_A.json')
            page = json.load(open(json_file))
            self.render('data_ocr.html', page=page, img=self.static_url('imgs/001_006_A.gif'))

        except Exception as e:
            return self.send_db_error(e, render=True)
