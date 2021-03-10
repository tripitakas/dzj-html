#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from bson.objectid import ObjectId
from .char import Char
from .base import CharHandler
from controller import errors as e
from controller import helper as h
from controller import validate as v


class CharDeleteApi(CharHandler):
    URL = '/api/(char)/delete'

    def post(self, collection):
        """批量删除"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if self.data.get('_id'):
                r = self.db[collection].delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_log('delete_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_log('delete_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class CharExtractImgApi(CharHandler):
    URL = '/api/char/extract_img'

    def post(self):
        """批量生成字图"""
        try:
            rules = [(v.not_empty, 'type'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)

            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = self.get_char_search_condition(self.data['search'])[0]
            count = self.db.char.count_documents(condition)
            self.db.char.update_many(condition, {'$set': {'img_need_updated': True}})
            if count:  # 启动脚本，生成字图
                regen = int(self.data.get('regen') in ['是', True])
                script = 'nohup python3 %s/utils/extract_img.py --username=%s --regen=%s >> log/extract_img_%s.log 2>&1 &'
                script = script % (h.BASE_DIR, self.username, regen, h.get_date_time(fmt='%Y%m%d%H%M%S'))
                print(script)
                os.system(script)
                self.send_data_response(count=count)
            else:
                self.send_error_response(e.no_object, message='找不到对应的字数据')

        except self.DbError as error:
            return self.send_db_error(error)


class CharTxtApi(CharHandler):
    URL = '/api/char/txt/@char_name'

    def merge_txt_logs(self, user_log, char):
        """合并用户的连续修改"""
        ori_logs = char.get('txt_logs') or []
        for i in range(len(ori_logs)):
            last = len(ori_logs) - 1 - i
            if ori_logs[last].get('user_id') == self.user_id:
                ori_logs.pop(last)
            else:
                break
        user_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
        return ori_logs + [user_log]

    def post(self, char_name):
        """聚类校对-更新单字的txt"""
        try:
            rules = [(v.not_empty, 'txt'), (v.is_txt, 'txt')]
            self.validate(self.data, rules)

            char = self.db.char.find_one({'name': char_name})
            if not char:
                return self.send_error_response(e.no_object, message='没有找到字符')
            if self.is_v_code(self.data['txt']) and not self.db.variant.find_one({'v_code': self.data['txt']}):
                return self.send_error_response(e.no_object, message='该编码对应的图片字不存在')
            # 检查数据等级和积分
            self.check_txt_level_and_point(self, char, self.data.get('task_type'))
            # 检查参数，设置更新
            fields = ['txt', 'is_vague', 'is_deform', 'uncertain', 'remark']
            if not [f for f in fields if (char.get(f) or False) != (self.data.get(f) or False)]:
                return self.send_error_response(e.not_changed, message='没有任何修改')
            # 按照格式设置字段，以便后续搜索
            update = {k: self.data[k] for k in fields if k in self.data}
            my_log = {k: self.data[k] for k in fields + ['task_type'] if k in self.data}
            update['txt_logs'] = self.merge_txt_logs(my_log, char)
            update['txt_level'] = self.get_user_txt_level(self, self.data.get('task_type'))
            self.db.char.update_one({'name': char_name}, {'$set': update})
            self.send_data_response(dict(txt_logs=update['txt_logs']))

            self.add_log('update_txt', char['_id'], char['name'], update)

        except self.DbError as error:
            return self.send_db_error(error)


class CharsTxtApi(CharHandler):
    URL = '/api/chars/txt'

    def post(self):
        """批量更新char"""
        try:
            fields = ['txt', 'is_vague', 'is_deform', 'uncertain', 'remark']
            rules = [(v.not_empty, 'names'), (v.not_none, 'field', 'value'), (v.in_list, 'field', fields)]
            self.validate(self.data, rules)

            field, value = self.data['field'], self.data['value']
            if field == 'txt' and self.is_v_code(value) and not self.db.variant.find_one({'v_code': value}):
                return self.send_error_response(e.no_object, message='该编码对应的图片字不存在')

            cond = {'name': {'$in': self.data['names']}, field: {'$ne': value}}
            chars = list(self.db.char.find(cond, {'name': 1, 'txt_level': 1, 'txt_logs': 1, 'tasks': 1}))
            log = dict(un_changed=[], level_unqualified=[], point_unqualified=[])
            log['un_changed'] = set(self.data['names']) - set(c['name'] for c in chars)
            # 检查数据权限和积分
            qualified = []
            for char in chars:
                r = self.check_txt_level_and_point(self, char, self.data.get('task_type'), False)
                if isinstance(r, tuple):
                    if r[0] == e.data_level_unqualified[0]:
                        log['level_unqualified'].append(char['name'])
                    elif r[0] == e.data_point_unqualified[0]:
                        log['point_unqualified'].append(char['name'])
                else:
                    qualified.append(char)

            # 检查用户是否修改过字符
            new_update, old_update = [], []
            for char in qualified:
                if char.get('txt_logs') and [log for log in char['txt_logs'] if log.get('user_id') == self.user_id]:
                    old_update.append(char['name'])
                else:
                    new_update.append(char['name'])

            # 更新char表的txt/txt_level等字段
            info = {field: value, 'txt_level': self.get_user_txt_level(self, self.data.get('task_type'))}
            self.db.char.update_many({'name': {'$in': new_update + old_update}}, {'$set': info})
            if new_update:
                self.db.char.update_many({'name': {'$in': new_update}, 'txt_logs': None}, {'$set': {'txt_logs': []}})
                self.db.char.update_many({'name': {'$in': new_update}}, {'$addToSet': {'txt_logs': {
                    **info, 'user_id': self.user_id, 'username': self.username,
                    'create_time': self.now(), 'updated_time': self.now()
                }}})
            if old_update:
                cond = {'name': {'$in': old_update}, 'txt_logs.user_id': self.user_id}
                self.db.char.update_many(cond, {'$set': {
                    'txt_logs.$.' + field: info[field],
                    'txt_logs.$.txt_level': info['txt_level'],
                    'txt_logs.$.updated_time': self.now(),
                }})
            log['updated'] = new_update + old_update
            self.send_data_response({k: l for k, l in log.items() if l})
            self.add_log('update_txt', None, new_update + old_update, info)

        except self.DbError as error:
            return self.send_db_error(error)


class CharSourceApi(CharHandler):
    URL = '/api/char/source'

    def post(self):
        """批量更新批次"""
        try:
            rules = [(v.not_empty, 'type', 'source'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)

            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = Char.get_char_search_condition(self.data['search'])[0]
            r = self.db.char.update_many(condition, {'$set': {'source': self.data['source']}})
            self.send_data_response(dict(matched_count=r.matched_count))
            self.add_log('update_char', self.data['_ids'], None, dict(source=self.data['source']))

        except self.DbError as error:
            return self.send_db_error(error)
