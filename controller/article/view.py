#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
import math
from controller import errors
from controller.base import BaseHandler


class ListArticleHandler(BaseHandler):
    URL = '/article/list'

    def get(self):
        """ 文章列表"""
        try:
            condition = {}
            q = self.get_query_argument('q', '')
            if q:
                condition['$or'] = [{f: {'$regex': '.*%s.*' % q}} for f in ['title', 'content']]
            query = self.db.article.find(condition)
            order = self.get_query_argument('order', '-_id')
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
            self.render('article.html', q=q, articles=articles, pager=pager, order=order)

        except Exception as e:
            return self.send_db_error(e, render=True)


class EditArticleHandler(BaseHandler):
    URL = ['/article/add', '/article/update/@article_id']

    def get(self, article_id=None):
        """ 新建或修改文章的页面"""
        try:
            article = article_id and self.db.article.find_one({'article_id': article_id})
            if article_id and not article:
                return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id)
            self.render('article_edit.html', article=article, article_id=article_id or '')
        except Exception as e:
            return self.send_db_error(e, render=True)


class ViewArticleHandler(BaseHandler):
    URL = '/article/@article_id'

    def get(self, article_id):
        """查看文章的页面"""
        try:
            article = self.db.article.find_one({'article_id': article_id})
            if not article:
                return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id)
            self.render('article_view.html', article=article, article_id=article_id)

        except Exception as e:
            return self.send_db_error(e, render=True)
