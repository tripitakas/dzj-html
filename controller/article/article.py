#!/usr/bin/env python
# -*- coding: utf-8 -*-

import controller.validate as v
from controller.model import Model


class Article(Model):
    collection = 'article'
    fields = [
        {'id': 'title', 'name': '标题'},
        {'id': 'article_id', 'name': '标识'},
        {'id': 'category', 'name': '分类'},
        {'id': 'active', 'name': '是否发布'},
        {'id': 'content', 'name': '内容', 'show_type': 'none'},
    ]
    rules = [
        (v.not_empty, 'title', 'article_id', 'category'),
        (v.is_article, 'article_id'),
    ]
    primary = 'article_id'
    search_fields = ['title', 'content']
    search_tip = '请搜索标题或内容'
    page_title = '文章管理'
    operations = [
        {'operation': 'add-article', 'label': '新增记录', 'url': '/article/add'},
    ]
    actions = [  # 列表操作
        {'id': 'article-view', 'label': '查看'},
        {'id': 'article-update', 'label': '修改'},
        {'id': 'article-remove', 'label': '删除'},
    ]
