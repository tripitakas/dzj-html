#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import csv
import json
from functools import cmp_to_key
from bson.objectid import ObjectId
import controller.errors as e
import controller.validate as v
from controller.helper import cmp_page_code


class Data(object):
    fields = []  # 字段定义，格式如[['volume_code', '册编码'], ...]
    int_fields = []  # 整型字段
    rules = []  # 数据校验规则
    key = ''  # 数据主键

    @classmethod
    def get_fields(cls):
        return [s[0] for s in cls.fields]

    @classmethod
    def get_field_name(cls, field):
        names = [s[1] for s in cls.fields if s[0] == field]
        return names and names[0]

    @classmethod
    def get_field_by_name(cls, name):
        if re.match(r'[0-9a-zA-Z_]+', name):
            return name
        else:
            fields = [s[0] for s in cls.fields if s[1] == name]
            return fields and fields[0] or ''

    @classmethod
    def validate(cls, doc):
        assert isinstance(doc, dict)
        err = v.validate(doc, cls.rules)
        return err

    @classmethod
    def get_doc(cls, doc):
        for k in list(doc.keys()):
            if k not in cls.get_fields() + ['_id']:
                doc.pop(k, 0)
            if k in cls.int_fields:
                doc[k] = int(doc[k]) if doc.get(k) else None

        if doc.get('_id'):
            doc['_id'] = ObjectId(str(doc['_id']))
        else:
            doc.pop('_id', 0)  # 删除空_id
        return doc

    @classmethod
    def ignore_existed_check(cls, doc):
        """ 哪些情况忽略重复检查 """
        return False

    @classmethod
    def save_one(cls, db, collection, doc):
        """ 插入或更新一条记录
        :param db 数据库连接
        :param collection: 准备插入哪个集合
        :param doc: 准备插入的数据
        """
        doc = cls.get_doc(doc)
        err = cls.validate(doc)
        if err:
            return dict(status='failed', errors=err)

        if doc.get('_id'):  # 更新
            data = db[collection].find_one({'_id': ObjectId(doc.get('_id'))})
            if data:
                r = db[collection].update_one({'_id': doc.get('_id')}, {'$set': doc})
                if not r.modified_count:
                    return dict(status='failed', errors=e.not_changed)
                return dict(status='success', id=doc.get('_id'), update=True, insert=False)
            else:
                return dict(status='failed', errors=e.tptk_id_not_existed)
        else:  # 新增
            if cls.ignore_existed_check(doc) is False and not db[collection].find_one({cls.key: doc[cls.key]}):
                r = db[collection].insert_one(doc)
                return dict(status='success', id=r.inserted_id, update=False, insert=True)
            else:
                return dict(status='failed', errors=e.tptk_code_existed)

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
        # 从文件流中读取数据
        if not docs and file_stream:
            rows = list(csv.reader(file_stream))
            heads = [cls.get_field_by_name(r) for r in rows[0]]
            need_fields = [cls.get_field_name(r) for r in cls.get_fields() if r not in heads]
            if need_fields:
                return dict(status='failed', code=e.tptk_field_error[0],
                            message='缺以下字段：%s' % ','.join(need_fields))
            docs = [{heads[i]: item for i, item in enumerate(row)} for row in rows[1:]]

        # 逐个校验数据
        valid_docs, valid_codes, error_codes = [], [], []
        for i, doc in enumerate(docs):
            err = cls.validate(doc)
            if err:
                error_codes.append([doc.get(cls.key), err])
            elif cls.ignore_existed_check(doc) is False and doc.get(cls.key) in valid_codes:
                # 去掉重复数据
                error_codes.append([doc.get(cls.key), e.tptk_code_duplicated])
            else:
                valid_docs.append(cls.get_doc(doc))
                valid_codes.append(doc.get(cls.key))

        # 剔除数据库中的重复记录
        existed_docs = []
        if valid_docs:
            existed_record = list(db[collection].find({cls.key: {'$in': valid_codes}}))
            existed_codes = [i.get(cls.key) for i in existed_record]
            existed_docs = [i for i in valid_docs if i.get(cls.key) in existed_codes]
            valid_docs = [i for i in valid_docs if i.get(cls.key) not in existed_codes]

        # 更新数据库中的重复记录
        if update:
            for doc in existed_docs:
                if updated_fields:
                    doc = {k: v for k, v in doc.items() if k in updated_fields}
                assert cls.key in doc
                db[collection].update_one({cls.key: doc.get(cls.key)}, {'$set': doc})

        # 插入新的数据记录
        if valid_docs:
            db[collection].insert_many(valid_docs)

        error_tip = '：' + ','.join([i[0] for i in error_codes]) if error_codes else ''
        message = '导入%s，总共%s条记录，插入%s条，%s条旧数据，更新%s条，%s条无效数据%s。' % (
            collection, len(docs), len(valid_docs), len(existed_docs), len(existed_docs) if update else 0,
            len(error_codes), error_tip)
        print(message)

        return dict(status='success', errors=error_codes, message=message)


class Tripitaka(Data):
    fields = [['tripitaka_code', '编码'], ['name', '藏名'], ['short_name', '简称'], ['store_pattern', '存储模式'],
              ['img_available', '图片是否就绪'], ['remark', '备注']]
    rules = [(v.not_empty, 'tripitaka_code', 'name'),
             (v.is_tripitaka, 'tripitaka_code')]
    key = 'tripitaka_code'


class Reel(Data):
    fields = [['uni_sutra_code', '统一经编码'], ['sutra_code', '经编码'], ['sutra_name', '经名'],
              ['reel_code', '卷编码'], ['reel_no', '卷序号'], ['start_volume', '起始册'],
              ['start_page', '起始页'], ['end_volume', '终止册'], ['end_page', '终止页'],
              ['remark', '备注']]
    int_fields = ['reel_no', 'start_page', 'end_page']
    rules = [(v.not_empty, 'sutra_code'),
             (v.is_digit, 'reel_no', 'start_page', 'end_page'),
             (v.is_sutra, 'sutra_code'),
             (v.is_reel, 'reel_code')]
    key = 'reel_code'

    @classmethod
    def ignore_existed_check(cls, doc):
        # 卷序号为0时不做重复检查
        return str(doc.get('reel_no')) == '0'


class Sutra(Data):
    fields = [['uni_sutra_code', '统一经编码'], ['sutra_code', '经编码'], ['sutra_name', '经名'],
              ['due_reel_count', '应存卷数'], ['existed_reel_count', '实存卷数'], ['author', '作译者'],
              ['trans_time', '翻译时间'], ['start_volume', '起始册'], ['start_page', '起始页'],
              ['end_volume', '终止册'], ['end_page', '终止页'], ['remark', '备注']]
    rules = [(v.not_empty, 'sutra_code', 'sutra_name'),
             (v.is_digit, 'due_reel_count', 'existed_reel_count', 'start_page', 'end_page'),
             (v.is_sutra, 'sutra_code')]
    key = 'sutra_code'


class Volume(Data):
    fields = [['tripitaka_code', '藏编码'], ['volume_code', '册编码'], ['envelop_no', '函序号'], ['volume_no', '册序号'],
              ['content_page_count', '正文页数'], ['content_pages', '正文页'], ['front_cover_pages', '封面页'],
              ['back_cover_pages', '封底页'], ['remark', '备注']]
    rules = [(v.not_empty, 'volume_code', 'tripitaka_code', 'volume_no'),
             (v.is_tripitaka, 'tripitaka_code'),
             (v.is_volume, 'volume_code'),
             (v.is_digit, 'volume_no')]
    key = 'volume_code'

    @classmethod
    def get_doc(cls, doc):
        doc = super().get_doc(doc)

        if doc.get('content_pages') and isinstance(doc['content_pages'], str):
            content_pages = json.loads(doc['content_pages'].replace("'", '"'))
            content_pages.sort(key=cmp_to_key(cmp_page_code))
            doc['content_pages'] = content_pages
        doc['content_page_count'] = len(doc['content_pages'])

        if doc.get('front_cover_pages') and isinstance(['front_cover_pages'], str):
            front_cover_pages = json.loads(doc['front_cover_pages'].replace("'", '"'))
            front_cover_pages.sort(key=cmp_to_key(cmp_page_code))
            doc['front_cover_pages'] = front_cover_pages

        if doc.get('back_cover_pages') and isinstance(['back_cover_pages'], str):
            back_cover_pages = json.loads(doc['back_cover_pages'].replace("'", '"'))
            back_cover_pages.sort(key=cmp_to_key(cmp_page_code))
            doc['back_cover_pages'] = back_cover_pages

        return doc


class Page(Data):
    fields = [['name', '页编码'], ['width', '宽度'], ['height', '高度'], ['img_path', '图片路径'],
              ['img_cloud_path', '云图路径'], ['uni_sutra_code', '统一经编码'], ['sutra_code', '经编码'],
              ['reel_code', '卷编码'], ['reel_page_no', '卷内页序号'], ['lock', '数据锁'],
              ['box_stage', '框阶段'], ['text_stage', '文本阶段'],
              ['blocks', '栏框'], ['columns', '列框'], ['chars', '字框'],
              ['ocr', 'OCR'], ['ocr_col', '列OCR'],
              ['text', '文本'], ['txt_html', '文本HTML']]
    rules = [(v.not_empty, 'name'),
             (v.is_page, 'name'),
             (v.is_sutra, 'uni_sutra_code'),
             (v.is_sutra, 'sutra_code'),
             (v.is_reel, 'reel_code'),
             (v.is_digit, 'reel_page_no')]
    key = 'name'

    @classmethod
    def metadata(cls):
        return dict(name='', width='', height='', img_suffix='', img_path='', img_cloud_path='',
                    sutra_code='', uni_sutra_code='', reel_code='', reel_page_no='', lock={},
                    box_stage='', text_stage='', blocks=[], columns=[], chars=[],
                    ocr='', ocr_col='', text='', txt_html='')

    @classmethod
    def insert_new(cls, db, file_stream=None):
        """ 插入新页面
        :param db 数据库连接
        :param file_stream 已打开的文件流。
        :return {status: 'success'/'failed', code: '',  message: '...', errors:[]}
        """
        result = json.load(file_stream)
        page_names = [r.split('.')[0] for r in result]
        name2suffix = {r.split('.')[0]: r.split('.')[1] if '.' in r else None for r in result}
        # 检查重复时，仅仅检查页码，不检查后缀
        existed_pages = list(db.page.find({'name': {'$in': page_names}}, {'name': 1}))
        new_names = set(page_names) - set([p['name'] for p in existed_pages])
        pages = []
        for page_name in new_names:
            page = cls.metadata()
            s = page_name.split('.')
            page['name'] = s[0]
            page['img_suffix'] = name2suffix.get(page_name)
            pages.append(page)
        if pages:
            r = db.page.insert_many(pages)
        message = '导入page，总共%s条记录，插入%s条，%s条旧数据。' % (len(page_names), len(pages), len(existed_pages))
        print(message)
        return dict(status='success', message=message, inserted_ids=r.inserted_ids if pages else [])
