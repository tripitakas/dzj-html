#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR页面
@time: 2019/9/2
"""
from controller.base import BaseHandler
from controller.data.ocr_api import RecognitionApi
from os import path
import json


class RecognitionHandler(BaseHandler):
    URL = ['/data/ocr', '/data/ocr/@img_file']

    def get(self, img_file=''):
        """ 藏经OCR页面 """
        try:
            img = self.static_url('upload/ocr/' + img_file if img_file else 'imgs/1_6A.gif')
            s_path = path.join(self.application.BASE_DIR, 'static')
            json_file = path.join(s_path, 'upload', 'ocr', img_file.split('.')[0] + '.json'
                                  ) if img_file else path.join(s_path, 'imgs', '1_6A.gif')
            page = json.load(open(json_file))
            self.render('data_ocr.html', page=RecognitionApi.ocr2page(page), img=img)

        except Exception as e:
            return self.send_db_error(e, render=True)
