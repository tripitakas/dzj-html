#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import controller.validate as v
from controller import helper as h
from controller.model import Model


class Article(Model):
    primary = 'article_id'
    collection = 'article'
    fields = {
        'no': {'name': '序号'},
        'title': {'name': '标题'},
        'title_link': {'name': '标题链接'},
        'article_id': {'name': '文章id'},
        'category': {'name': '分类', 'filter': {'帮助': '帮助', '公告': '公告', '通知': '通知'}},
        'active': {'name': '是否已发布', 'filter': {'是': '是', '否': '否'}},
        'content': {'name': '内容'},
        'author_name': {'name': '创建人'},
        'updated_by': {'name': '修改人'},
        'create_time': {'name': '创建时间'},
        'updated_time': {'name': '修改时间'},
    }
    rules = [
        (v.not_empty, 'title', 'article_id', 'category'),
        (v.is_article, 'article_id'),
    ]

    @classmethod
    def get_article_search_condition(cls, request_query):
        condition, params = dict(), dict()
        for field in ['category', 'active']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        return condition, params
