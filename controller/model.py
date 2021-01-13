#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 数据模型定义类
数据库字段(fields)定义格式如下:
{
    'id': '',  # 字段id
    'name': '',  # 字段名称
    'type': 'str',  # 存储类型，默认为str，其它如int/boolean等
    'input_type': 'text',  # 输入类型，默认为text，其它如radio/select/textarea等
    'options': [],  # 输入选项。如果输入类型为radio或select，则可以通过options提供对应的选项
}
@time: 2019/12/10
"""
import re
import csv
import math
import controller.errors as e
import controller.validate as v
from controller.helper import prop
from bson.objectid import ObjectId


class Model(object):
    """ 数据库参数"""
    collection = ''  # 数据库表名
    fields = [  # 数据库字段定义
        {'id': 'id1', 'name': 'name1', 'type': 'str', 'input_type': 'text'},
        {'id': 'id2', 'name': 'name2', 'type': 'int', 'input_type': 'radio', 'options': []},
    ]
    primary = ''  # 主键
    rules = []  # 校验规则

    """ 前端列表页面参数"""
    page_size = None  # 每页显示多少条
    page_title = ''  # 页面title
    search_tips = ''  # 查询提示
    search_fields = []  # 查询哪些字段
    table_fields = [dict(id='', name='')]  # 列表包含哪些字段
    hide_fields = []  # 列表默认隐藏哪些字段
    info_fields = []  # 列表action操作需要哪些字段信息
    operations = [  # 批量操作
        {'operation': 'btn-add', 'label': '新增记录'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    img_operations = ['config', 'help']
    actions = [  # 单条记录包含哪些操作
        {'action': 'btn-view', 'label': '查看'},
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
    ]
    update_fields = [dict(id='', name='', input_type='', options=[])]  # update模态框包含哪些字段
    com_fields = [
        {'id': 'create_time', 'name': '创建时间'},
        {'id': 'updated_time', 'name': '修改时间'},
    ]

    @classmethod
    def get_template_kwargs(cls, fields=None):
        fields = fields if fields else [
            'page_title', 'search_tips', 'search_fields', 'table_fields', 'hide_fields',
            'info_fields', 'operations', 'img_operations', 'actions', 'update_fields'
        ]
        return {f: getattr(cls, f) for f in fields}

    @staticmethod
    def prop(obj, key, default=None):
        return prop(obj, key, default=default)

    @classmethod
    def validate(cls, doc, rules=None):
        rules = cls.rules if not rules else rules
        return v.validate(doc, rules)

    @classmethod
    def get_fields(cls):
        return [f['id'] for f in cls.fields + cls.com_fields]

    @classmethod
    def get_need_fields(cls):
        # 设置必须字段，新增数据或批量上传时使用
        return [f['id'] for f in cls.fields]

    @classmethod
    def field_names(cls):
        return {f['id']: f['name'] for f in cls.fields}

    @classmethod
    def get_field_name(cls, field):
        for f in cls.fields:
            if f['id'] == field:
                return f['name']
        for f in cls.com_fields:
            if f['id'] == field:
                return f['name']
        return field

    @classmethod
    def get_field_type(cls, field):
        for f in cls.fields:
            if f['id'] == field:
                return f.get('type') or 'str'

    @classmethod
    def get_field_by_name(cls, name):
        if re.match(r'[0-9a-zA-Z_]+', name):
            return name
        for f in cls.fields:
            if f['name'] == name:
                return f['id']
        return name

    @classmethod
    def pack_doc(cls, doc, self=None, exclude_none=False):
        d = {k: v for k, v in doc.items() if k in cls.get_fields()}
        if exclude_none:
            d = {k: v for k, v in d.items() if v is not None}
        if doc.get('_id'):
            d['_id'] = ObjectId(str(doc['_id']))
        return d

    @classmethod
    def reset_order(cls, order):
        """ 重置order排序"""
        return order

    @classmethod
    def find_by_page(cls, self, condition=None, search_fields=None, default_order='', projection=None):
        """ 查找数据库中的记录，按页返回结果"""
        condition = condition or {}
        q = self.get_query_argument('q', '')
        search_fields = search_fields or cls.search_fields
        if q and search_fields:
            m = re.match(r'["\'](.*)["\']', q)
            condition['$or'] = [{k: m.group(1) if m else {'$regex': q, '$options': '$i'}} for k in search_fields]
        query = self.db[cls.collection].find(condition)
        if projection:
            query = self.db[cls.collection].find(condition, projection)
        order = self.get_query_argument('order', default_order)
        if order:
            o, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            query.sort(cls.reset_order(o), asc)

        if condition:
            doc_count = self.db[cls.collection].count_documents(condition)
        else:
            doc_count = self.db[cls.collection].estimated_document_count(filter=condition)
        cur_page = int(self.get_query_argument('page', 1))
        page_size = int(self.get_query_argument('page_size', 0) or hasattr(self, 'page_size') and self.page_size
                        or self.get_config('pager.page_size'))
        max_page = math.ceil(doc_count / page_size)
        cur_page = max_page if max_page and max_page < cur_page else cur_page
        docs = list(query.skip((cur_page - 1) * page_size).limit(page_size))
        pager = dict(cur_page=cur_page, doc_count=doc_count, page_size=page_size)
        return docs, pager, q, order

    @classmethod
    def aggregate_by_page(cls, self, condition=None, aggregates=None, default_order='', projection=None):
        """ 聚合数据库中的记录，按页返回结果"""
        condition = condition or {}
        aggregates = aggregates or []
        q = self.get_query_argument('q', '')
        if q and cls.search_fields:
            condition['$or'] = [{k: {'$regex': q, '$options': '$i'}} for k in cls.search_fields]
        aggregates.append({'$match': condition})
        if projection:
            aggregates.append({'$project': projection})
        order = self.get_query_argument('order', default_order)
        if order:
            o, asc = (order[1:], -1) if order[0] == '-' else (order, 1)
            aggregates.append({'$sort': {o: asc}})
        doc_count = len(list(self.db[cls.collection].aggregate(aggregates)))
        cur_page = int(self.get_query_argument('page', 1))
        page_size = int(self.get_query_argument('page_size', prop(self.config, 'pager.page_size', 10)))
        max_page = math.ceil(doc_count / page_size)
        cur_page = max_page if max_page and max_page < cur_page else cur_page
        aggregates.append({'$skip': (cur_page - 1) * page_size})
        aggregates.append({'$limit': page_size})
        docs = list(self.db[cls.collection].aggregate(aggregates))
        pager = dict(cur_page=cur_page, doc_count=doc_count, page_size=page_size)
        return docs, pager, q, order

    @classmethod
    def ignore_existed_check(cls, doc):
        """ 哪些情况忽略重复检查"""
        return False

    @classmethod
    def save_one(cls, db, collection, doc, rules=None, self=None):
        """ 插入或更新一条记录
        :param db 数据库连接
        :param collection: 准备插入哪个集合
        :param doc: 准备插入哪条数据
        :param rules: 数据验证规则
        :param self: 调用函数的handler
        """
        doc = cls.pack_doc(doc, self)
        errs = cls.validate(doc, rules)
        if errs:
            return dict(status='failed', errors=errs)

        if doc.get('_id'):  # 更新
            item = db[collection].find_one({'_id': doc.get('_id')})
            if item:
                r = db[collection].update_one({'_id': doc.get('_id')}, {'$set': doc})
                if not r.modified_count:
                    return dict(status='failed', errors=e.not_changed)
                return dict(status='success', id=doc.get('_id'), doc=doc, update=True, insert=False)
            else:
                return dict(status='failed', errors=e.no_object)
        else:  # 新增
            condition = {cls.primary: doc.get(cls.primary, '')}
            if cls.ignore_existed_check(doc) is False and not db[collection].find_one(condition):
                r = db[collection].insert_one(doc)
                return dict(status='success', id=r.inserted_id, doc=doc, update=False, insert=True)
            else:
                return dict(status='failed', errors=e.code_existed)

    @classmethod
    def save_many(cls, db, collection, docs=None, file_stream=None, update=True, updated_fields=None):
        """ 批量插入或更新数据
        :param db 数据库连接
        :param collection 待插入的数据集
        :param docs 待插入的数据。
        :param update 是否更新旧数据。
        :param updated_fields 更新哪些字段。默认为空，更新所有字段。
        :param file_stream 已打开的文件流。docs不为空时，将忽略这个字段。
        :return {status: 'success'/'failed', code: '',  message: '...', errors:[]}
        """

        def is_valid(d):
            return len([v for v in d.values() if v]) > 0

        # 从文件流中读取数据
        if not docs and file_stream:
            rows = list(csv.reader(file_stream))
            heads = [cls.get_field_by_name(r) for r in rows[0]]
            need_fields = [cls.get_field_name(r) for r in cls.get_need_fields() if r not in heads]
            if need_fields:
                message = '以下字段缺失：%s' % ', '.join(need_fields)
                return dict(status='failed', code=e.field_error[0], message=message)
            over_fields = [r for r in heads if r and r not in cls.get_fields()]
            if over_fields:
                message = '以下字段多余：%s' % ', '.join(over_fields)
                return dict(status='failed', code=e.field_error[0], message=message)
            docs = [{heads[i]: item for i, item in enumerate(row) if heads[i]} for row in rows[1:]]
            docs = [d for d in docs if is_valid(d)]
        # 逐个校验数据
        valid_docs, valid_codes, error_codes = [], [], []
        for i, doc in enumerate(docs):
            err = cls.validate(doc)
            if err:
                error_codes.append([doc.get(cls.primary), list(err.items())[0][1]])
            elif cls.ignore_existed_check(doc) is False and doc.get(cls.primary) in valid_codes:
                # 去掉重复数据
                error_codes.append([doc.get(cls.primary), e.code_duplicated[1]])
            else:
                valid_docs.append(cls.pack_doc(doc))
                valid_codes.append(doc.get(cls.primary))
        # 分离数据库中的重复记录
        existed_docs = []
        if valid_docs:
            existed_record = list(db[collection].find({cls.primary: {'$in': valid_codes}}))
            existed_codes = [i.get(cls.primary) for i in existed_record]
            existed_docs = [i for i in valid_docs if i.get(cls.primary) in existed_codes]
            valid_docs = [i for i in valid_docs if i.get(cls.primary) not in existed_codes]

        updated_names, add_names = [], []
        # 更新数据库中的重复记录
        if update:
            for doc in existed_docs:
                if updated_fields:
                    doc = {k: v for k, v in doc.items() if k in updated_fields}
                assert cls.primary in doc
                db[collection].update_one({cls.primary: doc.get(cls.primary)}, {'$set': doc})
                updated_names.append(str(doc.get(cls.primary)))
        # 插入新的数据记录
        if valid_docs:
            db[collection].insert_many(valid_docs)
            add_names = [str(doc.get(cls.primary)) for doc in valid_docs]

        error_tip = '：' + ','.join([i[0] for i in error_codes]) if error_codes else ''
        message = '导入%s，总共%s条记录，插入%s条新数据，更新%s条（%s条旧数据），%s条无效数据%s。' % (
            collection, len(docs), len(valid_docs),
            len(existed_docs) if update else 0, len(existed_docs),
            len(error_codes), error_tip)
        print(message)

        return dict(status='success', target_ids=updated_names + add_names, errors=error_codes, message=message)
