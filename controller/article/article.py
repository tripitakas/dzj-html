#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import controller.validate as v
from controller import helper as h
from controller.model import Model


class Article(Model):
    collection = 'article'
    fields = [
        {'id': 'no', 'name': '序号'},
        {'id': 'title', 'name': '标题'},
        {'id': 'title_link', 'name': '标题链接'},
        {'id': 'article_id', 'name': '标识'},
        {'id': 'category', 'name': '分类'},
        {'id': 'active', 'name': '是否发布'},
        {'id': 'content', 'name': '内容', 'show_type': 'none'},
        {'id': 'author_name', 'name': '创建人'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_by', 'name': '修改人'},
        {'id': 'updated_time', 'name': '修改时间'},
    ]
    rules = [
        (v.not_empty, 'title', 'article_id', 'category'),
        (v.is_article, 'article_id'),
    ]
    primary = 'article_id'

    page_title = '文章管理'
    search_tips = '请搜索标题或内容'
    search_fields = ['title', 'content']
    table_fields = [dict(id=f['id'], name=f['name']) for f in fields if f['id'] not in ['content']]
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'),
                          options=f.get('options', [])) for f in fields]
    operations = [  # 列表包含哪些批量操作
        {'operation': 'article-add', 'label': '新增文章'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    actions = [  # 列表单条记录包含哪些操作
        {'action': 'article-view', 'label': '查看'},
        {'action': 'article-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]

    @classmethod
    def get_article_search_condition(cls, request_query):
        """ 获取文章的查询条件"""
        request_query = re.sub('[?&]?from=.*$', '', request_query)
        condition, params = dict(), dict()
        for field in ['category', 'active']:
            value = h.get_url_param(field, request_query)
            if value:
                params[field] = value
                condition.update({field: value})
        return condition, params
