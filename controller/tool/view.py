#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import json
from os import path
from .ocr import ocr2page
import controller.errors as errors
from controller.base import BaseHandler


class OcrHandler(BaseHandler):
    URL = '/tool/ocr'

    def get(self):
        """ 藏经OCR页面 """
        self.render('tool_ocr.html')


class OcrViewHandler(BaseHandler):
    URL = '/tool/ocr/@img_file'

    def get(self, img_name):
        """ 藏经OCR页面 """
        try:
            upload_ocr = path.join(self.application.BASE_DIR, 'static', 'upload', 'ocr')
            if not path.exists(path.join(upload_ocr, img_name)):
                return self.send_error_response(errors.ocr_img_not_existed, render=True)
            json_file = path.join(upload_ocr, img_name.split('.')[0] + '.json')
            if not path.exists(json_file):
                return self.send_error_response(errors.ocr_json_not_existed, render=True)

            page = json.load(open(json_file))
            page = ocr2page(page)
            self.render('tool_ocr_view.html', img_name=img_name, page=page,
                        img=self.static_url('upload/ocr/' + img_name))

        except Exception as e:
            return self.send_db_error(e, render=True)


class SearchCbetaHandler(BaseHandler):
    URL = '/tool/search'

    def get(self):
        """ 检索cbeta库 """
        self.render('tool_search.html')


class PunctuationHandler(BaseHandler):
    URL = '/tool/punctuate'

    def get(self):
        """ 自动标点 """
        self.render('tool_punctuate.html')
