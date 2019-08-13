#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 如是藏经、大藏经
"""
import re
import os.path as path
from functools import cmp_to_key
import controller.errors as errors
from controller.base import BaseHandler
from controller.helper import cmp_page_code


class TripitakaUploadApi(BaseHandler):
    URL = '/api/data/upload/tripitaka'

    def post(self):
        """ 批量上传藏经数据 """
        csv_file = self.request.files.get('csv')
        content = csv_file[0]['body']
        self.send_data_response()
