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
        {'action': 'article-update', 'label': '修改'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
