#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
import re
from controller import errors as e
from controller.base import BaseHandler
from controller.article.article import Article


class ArticleAdminHandler(BaseHandler, Article):
    URL = '/article/admin'

    table_fields = [
        {'id': 'no', 'name': '序号'},
        {'id': 'title', 'name': '标题'},
        {'id': 'article_id', 'name': '标识'},
        {'id': 'category', 'name': '分类', 'filter': {'帮助': '帮助', '公告': '公告', '通知': '通知'}},
        {'id': 'active', 'name': '是否发布', 'filter': {'是': '是', '否': '否'}},
        {'id': 'author_name', 'name': '创建人'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_by', 'name': '修改人'},
        {'id': 'updated_time', 'name': '修改时间'},
    ]

    def get(self):
        """ 文章管理"""
        try:
            kwargs = self.get_template_kwargs()
            cd, params = self.get_article_search_condition(self.request.query)
            docs, pager, q, order = self.find_by_page(self, cd, None, '-create_time', {'content': 0})
            self.render('article_admin.html', docs=docs, pager=pager, order=order, q=q, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class ArticleUpsertHandler(BaseHandler):
    URL = ['/article/add', '/article/update/@article_id']

    def get(self, article_id=None):
        """ 新建或修改文章"""
        try:
            article = article_id and self.db.article.find_one({'article_id': article_id}) or {}
            if article_id and not article:
                return self.send_error_response(e.no_object, message='文章%s不存在' % article_id)
            self.render('article_edit.html', article=article, article_id=article_id or '')
        except Exception as error:
            return self.send_db_error(error)


class ArticleViewHandler(BaseHandler):
    URL = '/article/@article_id'

    def get(self, article_id):
        """ 查看文章"""
        try:
            article = self.db.article.find_one({'article_id': article_id})
            if not article:
                return self.send_error_response(e.no_object, message='文章%s不存在' % article_id)
            self.render('article_view.html', article=article, article_id=article_id)

        except Exception as error:
            return self.send_db_error(error)


class ArticleListHandler(BaseHandler, Article):
    URL = '/(help|announce)'

    @classmethod
    def set_template_kwargs(cls, category):
        cls.search_tips = ''
        cls.search_fields = []
        cls.operations = []
        cls.img_operations = []
        cls.page_title = '帮助中心' if category == 'help' else '通知中心'

    def get(self, category):
        """ 帮助、通知中心"""

        def pack_content(content):
            size = 200
            content = content.replace('&nbsp;', '')
            content = re.sub(r'<.*?>', '', content)
            if len(content) > size:
                content = content[:size] + '...'
            return content

        try:
            self.set_template_kwargs(category)
            kwargs = self.get_template_kwargs()
            condition = {'category': '帮助' if category == 'help' else '通知', 'active': '是'}
            docs, pager, q, order = self.find_by_page(self, condition, default_order='no')
            self.render('article_list.html', docs=docs, pager=pager, order=order, q=q, pack=pack_content,
                        **kwargs)

        except Exception as error:
            return self.send_db_error(error)
