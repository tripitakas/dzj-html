#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
from controller.base import BaseHandler


class EditArticleHandler(BaseHandler):
    URL = '/article/edit/@article_id'

    def get(self, article_id):
        """新建或修改文章的页面"""
        try:
            self.render('article_edit.html')
        except Exception as e:
            return self.send_db_error(e, render=True)


class ViewArticleHandler(BaseHandler):
    URL = '/article/@article_id'

    def get(self, article_id):
        """查看文章的页面"""
        try:
            self.render('article_view.html')
        except Exception as e:
            return self.send_db_error(e, render=True)
