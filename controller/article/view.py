#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
import re
import math
from bson.objectid import ObjectId
from controller import errors
from controller.base import BaseHandler


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

        cond = {'_id': ObjectId(article_id)} if re.match('[0-9a-zA-Z]{24}', article_id) else {'article_id': article_id}
        article = self.db.article.find_one(cond) if len(article_id) > 3 else {}
        if article is None:
            if '-' in article_id:
                article = dict(category='帮助', title=article_id)
            else:
                return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id, render=True)
        self.render('article_edit.html', article=article, article_id=article_id)


class ViewArticleHandler(BaseHandler):
    URL = '/article/@article_id'

    def get(self, article_id, x=1):
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


class HelpHandler(BaseHandler):
    URL = '/help'

    def get(self):
        """ 帮助中心"""
        try:
            q = self.get_query_argument('q', '')
            order = self.get_query_argument('order', '-_id')
            condition = {}
            if q:
                condition['$or'] = [{f: {'$regex': '.*%s.*' % q}} for f in ['title', 'content']]
            query = self.db.article.find(condition)
            if order:
                o, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
                query.sort(o, asc)

            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            item_count = self.db.article.count_documents(condition)
            max_page = math.ceil(item_count / page_size)
            cur_page = max_page if max_page and max_page < cur_page else cur_page
            articles = list(query.skip((cur_page - 1) * page_size).limit(page_size))

            pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
            self.render('help.html', q=q, articles=articles, pager=pager, order=order)
        except Exception as e:
            return self.send_db_error(e, render=True)
