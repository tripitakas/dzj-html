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

    page_title = '文章管理'
    search_fields = ['title', 'article_id', 'category', 'content']
    table_fields = ['no', 'title', 'article_id', 'category', 'active', 'author_name', 'updated_by', 'create_time',
                    'updated_time']
    operations = [
        {'operation': 'article-add', 'label': '新增文章'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    img_operations = ['config']
    actions = [
        {'action': 'article-view', 'label': '查看'},
        {'action': 'article-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]

    def get(self):
        """文章管理"""
        try:
            kwargs = self.get_template_kwargs()
            if self.get_hide_fields() is not None:
                kwargs['hide_fields'] = self.get_hide_fields()
            cond, params = self.get_article_search_condition(self.request.query)
            docs, pager, q, order = self.find_by_page(self, cond, None, '-create_time', {'content': 0})
            self.render('article_admin.html', docs=docs, pager=pager, order=order, q=q, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class ArticleUpsertHandler(BaseHandler):
    URL = ['/article/add', '/article/update/@article_id']

    def get(self, article_id=None):
        """新建或修改文章"""
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
        """查看文章"""
        try:
            article = self.db.article.find_one({'article_id': article_id})
            if not article:
                return self.send_error_response(e.no_object, message='文章%s不存在' % article_id)
            self.render('article_view.html', article=article, article_id=article_id)

        except Exception as error:
            return self.send_db_error(error)


class ArticleListHandler(BaseHandler, Article):
    URL = '/(help|announce)'

    @staticmethod
    def pack_content(content):
        size = 200
        content = content.replace('&nbsp;', '')
        content = re.sub(r'<.*?>', '', content)
        if len(content) > size:
            content = content[:size] + '...'
        return content

    def get_template_kwargs(self, fields=None):
        kwargs = super().get_template_kwargs()
        kwargs['search_fields'] = []
        kwargs['operations'] = []
        kwargs['img_operations'] = []
        return kwargs

    def get(self, category):
        """帮助、通知中心"""
        try:
            kwargs = self.get_template_kwargs()
            kwargs['page_title'] = '帮助中心' if category == 'help' else '通知中心'
            condition = {'category': '帮助' if category == 'help' else '通知', 'active': '是'}
            docs, pager, q, order = self.find_by_page(self, condition, default_order='no')
            self.render('article_list.html', docs=docs, pager=pager, order=order, q=q,
                        pack=self.pack_content, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
