#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经数据管理
@time: 2019/3/13
"""
import re
from bson import json_util
from controller import helper as h
from controller.base import BaseHandler
from controller.task.base import TaskHandler
from controller.data.data import Tripitaka, Volume, Sutra, Reel, Variant


class DataImportImageHandler(TaskHandler):
    URL = '/data/image'

    page_title = '导入页图片'
    search_tips = '请搜索网盘名称、导入文件夹'
    search_fields = ['params.pan_name', 'params.import_dir']
    operations = [
        {'operation': 'bat-remove', 'label': '批量删除', 'url': '/task/delete'},
        {'operation': 'btn-publish', 'label': '发布任务', 'data-target': 'publishModal'},
    ]
    img_operations = ['help']
    actions = [
        {'action': 'btn-detail', 'label': '详情'},
        {'action': 'btn-remove', 'label': '删除', 'url': '/task/delete'},
        {'action': 'btn-republish', 'label': '重新发布'},
    ]
    table_fields = [
        {'id': '_id', 'name': '主键'},
        {'id': 'params.pan_name', 'name': '网盘名称'},
        {'id': 'params.import_dir', 'name': '导入文件夹'},
        {'id': 'params.layout', 'name': '版面结构'},
        {'id': 'params.redo', 'name': '是否覆盖　<br/>已有图片'},
        {'id': 'status', 'name': '状态'},
        {'id': 'priority', 'name': '优先级', 'filter': TaskHandler.priorities},
        {'id': 'return_reason', 'name': '退回理由'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
        {'id': 'publish_time', 'name': '发布时间'},
        {'id': 'publish_by', 'name': '发布人'},
        {'id': 'picked_time', 'name': '领取时间'},
        {'id': 'picked_by', 'name': '领取人'},
        {'id': 'finished_time', 'name': '完成时间'},
    ]
    hide_fields = ['_id', 'return_reason', 'create_time', 'updated_time', 'publish_by']
    update_fields = []

    def get(self):
        """ 数据管理/页图片导入"""
        try:
            # 模板参数
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            # 检索条件
            condition = dict(task_type='import_image')
            priority = self.get_query_argument('priority', '')
            if priority:
                condition.update({'priority': int(priority)})
            # 查询数据
            docs, pager, q, order = self.find_by_page(self, condition, default_order='-publish_time')
            self.render(
                'data_image_import.html', docs=docs, pager=pager, order=order, q=q,
                format_value=self.format_value, **kwargs,
            )

        except Exception as error:
            return self.send_db_error(error)


class DataListHandler(BaseHandler):
    URL = '/data/(tripitaka|sutra|reel|volume)'

    def get(self, metadata):
        """ 数据管理"""
        try:
            model = eval(metadata.capitalize())
            kwargs = model.get_template_kwargs()
            kwargs['img_operations'] = ['config']
            kwargs['operations'] = [
                {'operation': 'btn-add', 'label': '新增记录'},
                {'operation': 'bat-remove', 'label': '批量删除'},
                {'operation': 'bat-upload', 'label': '批量上传', 'data-target': 'uploadModal'},
                {'operation': 'download-template', 'label': '下载模板', 'url': '/static/template/%s-sample.csv' % metadata},
            ]
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            docs, pager, q, order = model.find_by_page(self)
            self.render('data_list.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class VariantListHandler(BaseHandler, Variant):
    URL = '/data/variant'

    page_title = '异体字管理'
    table_fields = [
        {'id': 'uid', 'name': '编码'},
        {'id': 'txt', 'name': '异体字'},
        {'id': 'img_name', 'name': '异体字图'},
        {'id': 'normal_txt', 'name': '所属正字'},
        {'id': 'remark', 'name': '备注'},
        {'id': 'create_by', 'name': '创建人'},
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '更新时间'},
    ]
    info_fields = ['uid', 'txt', 'img_name', 'normal_txt', 'remark']
    operations = [
        {'operation': 'btn-add', 'label': '新增记录'},
        {'operation': 'bat-remove', 'label': '批量删除'},
        {'operation': 'btn-search', 'label': '综合检索', 'data-target': 'searchModal'},
    ]
    update_fields = [
        {'id': 'uid', 'name': '编码', 'readonly': True},
        {'id': 'txt', 'name': '异体字'},
        {'id': 'img_name', 'name': '异体字图'},
        {'id': 'normal_txt', 'name': '所属正字'},
        {'id': 'remark', 'name': '备注'},
    ]

    def format_value(self, value, key=None, doc=None):
        """ 格式化输出"""
        if key == 'img_name' and value:
            return '<div><img src="%s"></div><div>%s</div>' % (self.get_web_img(value, 'char'), value)
        return h.format_value(value, key, doc)

    def get(self):
        """ 数据管理"""
        try:
            kwargs = self.get_template_kwargs()
            key = re.sub(r'[\-/]', '_', self.request.path.strip('/'))
            hide_fields = json_util.loads(self.get_secure_cookie(key) or '[]')
            kwargs['hide_fields'] = hide_fields if hide_fields else kwargs['hide_fields']
            kwargs['img_operations'] = ['config']
            condition, params = Variant.get_variant_search_condition(self.request.query)
            docs, pager, q, order = Variant.find_by_page(self, condition, default_order='_id')
            self.render('data_variant_list.html', docs=docs, pager=pager, q=q, order=order, params=params,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
