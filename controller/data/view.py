#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from bson import json_util
from controller import errors as e
from controller import helper as h
from controller.task.task import Task
from controller.base import BaseHandler
from controller.data.data import Tripitaka, Volume, Sutra, Reel, Variant


class DataListHandler(BaseHandler):
    URL = '/data/(tripitaka|sutra|reel|volume|variant)'

    def get(self, metadata):
        """ 数据管理"""
        try:
            model = eval(metadata.capitalize())
            kwargs = model.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            kwargs['img_operations'] = ['config']
            kwargs['operations'] = [
                {'operation': 'btn-add', 'label': '新增记录'},
                {'operation': 'bat-remove', 'label': '批量删除'},
                {'operation': 'bat-upload', 'label': '批量上传', 'data-target': 'uploadModal'},
                {'operation': 'download-template', 'label': '下载模板',
                 'url': '/static/template/%s-sample.csv' % metadata},
            ]
            docs, pager, q, order = model.find_by_page(self)
            self.render('data_list.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
