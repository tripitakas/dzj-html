#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
from bson.objectid import ObjectId
from controller.base import BaseHandler
from controller import errors


class EditArticleHandler(BaseHandler):
    URL = '/article/edit/@article_id'

    def get(self, article_id):
        """新建或修改文章的页面"""
        try:
            self.edit(self, article_id)
        except Exception as e:
            return self.send_db_error(e, render=True)

    @staticmethod
    def edit(self, article_id):
        cond = {'article_id': article_id} if '-' in article_id else {'_id': ObjectId(article_id)}
        article = self.db.article.find_one(cond) if len(article_id) > 3 else {}
        if article is None:
            return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id, render=True)
        self.render('article_edit.html', article=article, article_id=article_id)


class ViewArticleHandler(BaseHandler):
    URL = '/article/@article_id'

    def get(self, article_id):
        """查看文章的页面"""
        try:
            cond = {'article_id': article_id} if '-' in article_id else {'_id': ObjectId(article_id)}
            article = self.db.article.find_one(cond)
            if article is None:
                if '-' in article_id:
                    return EditArticleHandler.edit(self, article_id)
                return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id, render=True)
            self.render('article_view.html', article=article, article_id=article_id)
        except Exception as e:
            return self.send_db_error(e, render=True)
