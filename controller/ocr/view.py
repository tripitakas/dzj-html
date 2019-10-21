#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR页面
@time: 2019/9/2
"""

import json
from os import path
from .api import RecognitionApi
import controller.errors as errors
from controller.base import BaseHandler


class RecognitionHandler(BaseHandler):
    URL = '/ocr'

    def get(self):
        """ 藏经OCR页面 """
        self.render('ocr_upload.html')


class RecognitionViewHandler(BaseHandler):
    URL = '/ocr/@img_file'

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
            page = RecognitionApi.ocr2page(page)
            self.render('ocr_view.html', img_name=img_name,  page=page,
                        img=self.static_url('upload/ocr/' + img_name))

        except Exception as e:
            return self.send_db_error(e, render=True)


class ImportImagesHandler(BaseHandler):
    URL = '/data/import_images'

    def get(self):
        """ 藏经图片的导入和OCR测试页面 """
        self.render('data_import_images.html')