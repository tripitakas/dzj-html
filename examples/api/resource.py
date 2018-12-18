#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/10/31
"""

from tornado.web import authenticated
from tornado.escape import json_decode
from api.base import BaseHandler, convert_bson, db_errors
from api import errors
from api.resource import base_res
from bson import ObjectId
from pymysql.cursors import DictCursor
import model.user as u
from datetime import datetime
import base64
import os
import re
import logging


class RemoveResourceHandler(BaseHandler):
    URL = '/api/res/del'

    @authenticated
    def post(self):
        """ 删除本人的资源 """
        rid = self.get_body_argument('id')
        title = self.get_body_argument('title')
        assert rid and title

        try:
            r = self.db.res.delete_one({'_id': ObjectId(rid), 'create_user': self.current_user.id})
            if not r.deleted_count:
                return self.send_error(errors.no_object)
            with self.connection as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT group_id FROM t_group_res WHERE res_id=%s', (rid,))
                    groups = [r[0] for r in cursor.fetchall()]
                    cursor.execute('DELETE FROM t_group_res WHERE res_id=%s', (rid,))
                    self.add_op_log(cursor, 'remove_res', file_id=rid, context=title + ',' + ','.join(groups))
            self.send_response()
        except db_errors as e:
            return self.send_db_error(e)


class UserResourcesHandler(BaseHandler):
    URL = '/api/res/user/(\w{16})'

    def get(self, user_id):
        """ 用户资源 """
        size = 20
        page = int(self.get_argument('page', 0))
        try:
            with self.connection as conn:
                self.update_login(conn)
                with conn.cursor() as cursor:
                    cursor.execute('SELECT name FROM t_user a WHERE id=%s', (user_id,))
                    user = cursor.fetchone()
                    if not user:
                        return self.send_error(errors.no_object)
                    user = dict(name=user[0], id=user_id)

            items = self.db.res.find({'create_user': user_id, 'published': 1, 'type': None}).skip(
                page * size).limit(size)
            self.send_response(dict(author=user, resources=base_res.convert_resources(self, items),
                                    page_size=size, page=page))
        except db_errors as e:
            return self.send_db_error(e)


class ResourceHandler(BaseHandler):
    URL = '/api/res/(me|new|\w{24})'

    @authenticated
    def get_my_resources(self):
        items = self.db.res.find({'create_user': self.current_user.id})
        items = [convert_bson(r) for r in items if not r.get('removed') and not(r.get('type') and r.get('published'))]
        groups = self.convert_for_send(self.get_shares(None, self.current_user.id))
        for r in items:
            r['groups'] = [[g['group_id'], g['nickname']] for g in groups if g['res_id'] == r['id']]
        self.send_response(base_res.convert_resources(self, items))

    def get(self, rid):
        """ 读取资源条目 """
        try:
            self.update_login()
            user_id = self.current_user and self.current_user.id
            if rid == 'me':
                self.get_my_resources()
            else:
                groups = self.convert_for_send(self.get_shares(rid))
                blocks = []
                item = convert_bson(self.db.res.find_one({'_id': ObjectId(rid)}))
                if not item or item.get('removed'):
                    return self.send_error(errors.no_object)
                if not groups and 'origin' in item:
                    groups = self.convert_for_send(self.get_shares(item['origin']))

                if item.get('type') == 'task':
                    item['finishes'] = [convert_bson(r) for r in list(
                        self.db.res.find({'origin': rid, 'type': 'task-do'})) if not r.get('removed')]
                    item['finishes'] = {r['create_user']: r for r in item['finishes']}
                    if self.get_argument('do', 0) and user_id and user_id in item['finishes']:
                        item = item['finishes'][user_id]
                else:
                    rs = [convert_bson(r) for r in self.db.res.find(dict(source=rid))
                          if r['update_time'] != r['create_time']]
                    item['clones'] = [dict(id=r['id'], create_time=r['create_time'][:16], author=r['author'],
                                           title=r['title']) for r in rs]

                base_res.convert_resource(self, item)
                for i, blk in enumerate(item['blocks']):
                    blk = blk.get('id') and convert_bson(self.db.block.find_one({'_id': ObjectId(blk.get('id'))}))
                    if blk and blk.get('content'):
                        blocks.append((blk['content'], i))
                        item['blocks'][i]['update_time'] = blk['update_time']
                if user_id != item['create_user']:
                    self.add_op_log(None, 'view_res', rid, context=item['create_user'],
                                    team=groups and groups[0]['group_id'] or '')
                self.send_response(dict(content=item, blocks=blocks, groups=groups))
        except db_errors as e:
            return self.send_db_error(e)

    @authenticated
    def post(self, rid):
        """ 保存资源条目 """

        def save_block(b, body, first=True):
            def handle_body(html):
                title = html and re.findall(r'<title>([^<]+?)</title>', html)
                title = title and title[0].strip()
                new_body = body
                if title:
                    a2 = re.sub(r'>[^<]+?<', '>%s<' % title,  a)
                    a2 = re.sub(r'href="[^"]+', 'href="' + url,  a2)
                    new_body = body.replace(a, a2.replace('target="_self"', 'target="_blank"'))
                if save_block(b, new_body, False) and save_blocks():
                    set_content_image()
                    save_content()

            def replace_url(m):
                old = m.group()
                m = m.group(2)
                return old.replace(m, '<a href="{0}" target="_blank">{0}</a>'.format(m))

            if first:
                body = re.sub(r'<p>(&nbsp;)*(http(s)?://[^<> &"]+)', replace_url, body)
            if first and re.search(r'<a href="http', body):
                a = (re.findall(r'(<a href="http[^>]+?>[^<]+?</a>)', body) + [''])[0]
                url = (re.findall(r'>([^<]+?)<', a) + [''])[0]
                if url.startswith('http'):
                    return self.fetch_html(url, handle_body)

            bid = b.get('id', 'new')
            id_time = BlockHandler.save(self, 'new' if b.get('origin') == bid else bid, b['type'], body)
            if not id_time:
                return
            if content.get('type') == 'task':
                b['editable'] = b.get('editable', 0)
            b['id'] = id_time[0]
            if id_time[1]:
                b['update_time'] = id_time[1]
            if id_time[2]:
                b['create_user'] = id_time[2]
            return True

        def save_blocks():
            self._auto_finish = False
            for body, index in blocks:
                b = content['blocks'][index]
                if index not in saved:
                    saved.append(index)
                    if not save_block(b, body):
                        return False
            return True

        def set_content_image():
            img_block = ([b for b in content['blocks'] if b.get('image') and b.get('width')] + [0])[0]
            if img_block and img_block.get('image_w'):
                content['image'] = img_block['image']
                content['image_w'] = img_block['image_w']
                content['image_h'] = img_block['image_h']
            elif content.get('image') and not content.get('image_w'):
                try:
                    filename = re.sub(r'^.+/php/', self.application.IMAGE_PATH + '/', content['image'])
                    content['image_w'], content['image_h'] = base_res.get_image_size(filename)
                except Exception as e:
                    logging.error(content['image'] + ': ' + str(e))

        def save_content():
            try:
                groups = [g for g in content.pop('groups', []) if g]
                content.pop('id', 0)
                content.pop('finishes', 0)
                content['blocks'] = [b for b in content['blocks'] if not b.get('removed')]
                first_save = content.get('source_user') and content['update_time'] == content['create_time']
                r_id = rid
                if rid == 'new' or content.get('origin') == rid:
                    content['update_time'] = content['create_time'] = datetime.now()
                    content['create_user'] = self.current_user.id
                    content['author'] = self.current_user.name
                    r = self.db.res.insert_one(content)
                    r_id = content['id'] = str(r.inserted_id)
                    self.add_op_log(None, 'add_res', file_id=r_id,
                                    context='%d blocks, %s' % (len(content['blocks']), content['title']))
                else:
                    content.pop('create_time', 0)
                    content.pop('update_time', 0)
                    content.pop('create_user', 0)
                    content.pop('author', 0)
                    r = self.db.res.update_one({'_id': ObjectId(rid)}, {'$set': content})
                    if not r.matched_count:
                        return self.send_error(errors.no_object)
                    if r.modified_count:
                        content['update_time'] = datetime.now()
                        content['changed_count'] = content.get('changed_count', 0) + 1
                        if not image_block and '?' not in content.get('image', ''):
                            content['image'] += '?outdated=1'
                        self.db.res.update_one({'_id': ObjectId(rid)}, {'$set': content})
                        self.add_op_log(None, 'save_res', file_id=rid,
                                        context='%d blocks, %s' % (len(content['blocks']), content['title']))

                shared = groups and self.share_in_groups(r_id, groups, content.get('type'), content.get('origin')) or 0
                convert_bson(content)
                if first_save:
                    self.notify_user_message(content['source_user'], '/r/' + r_id, 'clone_res', '改编资源')
                self.send_response(dict(id=r_id, update_time=content.get('update_time'), shared=shared,
                                        ids=[b.get('id', 0) for b in content['blocks']]))

            except db_errors as e:
                return self.send_db_error(e)

        content = json_decode(self.get_argument('content'))
        blocks = json_decode(self.get_argument('blocks'))

        if not(content.get('title') and content.get('blocks')):
            return self.send_error(errors.incomplete)

        image_block = None
        content.pop('changed', 0)
        for block in content['blocks']:
            block.pop('changed', 0)
            for k in list(block.keys()):
                if re.match(r'^[_$#]', k):
                    block.pop(k)
            if 'image' in block:
                block['image'] = re.sub(r'\?.+$', '', block['image'])
                image_block = image_block or block

        saved = []
        if save_blocks():
            set_content_image()
            save_content()

    def share_in_groups(self, rid, groups, rtype, task_id):
        ret = 0
        with self.connection as conn:
            for gid in groups:
                r = dict(res_id=rid, user_id=self.current_user.id, type=rtype, group_id=gid,
                         task_id=task_id, create_time=errors.get_date_time())
                sql2 = 'SELECT user_id FROM t_member WHERE group_id=%s and ' \
                       '(role="owner" or role="manager" or role="member") and user_id<>%s'
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(*self.insert_sql('t_group_res', r))
                        self.add_op_log(cursor, 'share_in_group', context=rid, team=gid)
                        ret += 1

                        cursor.execute(sql2, (gid, self.current_user.id))
                        for r in cursor.fetchall():
                            if rtype == 'task-do':
                                self.notify_user_message(r[0], '/r/' + task_id, 'share_in_group',
                                                         self.current_user.name + ' 完成任务')
                            else:
                                self.notify_user_message(r[0], '/g/' + gid, 'share_in_group',
                                                         self.current_user.name + ' 分享资源到班组')
                except db_errors as e:
                    logging.warning('share_in_groups: ' + str(e))
        return ret

    def get_shares(self, rid, user_id=None):
        sql = 'SELECT res_id,group_id,task_id,name as nickname FROM t_group_res r,t_group g ' \
              'WHERE group_id=g.id and res_id=%s ORDER BY r.create_time DESC'
        if user_id:
            sql = sql.replace('res_id=%s', 'user_id=%s')
        with self.connection as conn:
            with conn.cursor(DictCursor) as cursor:
                cursor.execute(sql, (user_id or rid,))
                return [self.fetch2obj(r, u.GroupResource) for r in cursor.fetchall()]


class BlockHandler(BaseHandler):
    URL = r'/api/block/(new|image|\w{24})'

    @authenticated
    def get(self, bid):
        """ 读取资源块的内容 """
        try:
            block = convert_bson(self.db.block.find_one({'_id': ObjectId(bid)}))
            if not block:
                return self.send_error(errors.no_object)
            self.send_response(block)
        except db_errors as e:
            return self.send_db_error(e)

    @authenticated
    def post(self, bid):
        """ 保存资源块的内容 """
        block = self.get_body_argument('block', 0)
        content = self.get_body_argument('content', 0)
        image = self.get_body_argument('image', 0)
        block = json_decode(block)

        if image and not content:
            assert block and len(image) > 10
            image = re.sub(r'^data:.*;base64', '', image)
            max_h = int(float(self.get_body_argument('height', 0)))
            image, w, h = self.save_image(block['create_time'][:7], block['id'] + '.png',
                                          base64.b64decode(image), max_h)
            if w and h:
                self.db.res.update_one({'_id': ObjectId(block['id'])},
                                       {'$set': dict(image=image, w=w, h=h)})
            return self.send_response(dict(image=image, w=w, h=h))

        id_time = self.save(self, 'new' if block.get('origin') == bid else bid, block['type'], content)
        if id_time:
            bid, time, create_user = id_time
            w = h = 0
            if image:
                image = time and len(image) > 10 and re.sub(r'^data:.*;base64', '', image)
                max_h = int(float(self.get_body_argument('height', 0)))
                if image:
                    image, w, h = self.save_image(time[:7], bid + '.png', base64.b64decode(image), max_h)
            self.send_response(dict(id=bid, update_time=time, image=image, create_user=create_user, w=w, h=h))

    def save_image(self, folder, name, image, height=0):
        img_path = os.path.join(self.application.IMAGE_PATH, folder)
        if not os.path.exists(img_path):
            os.mkdir(img_path)
        filename = os.path.join(img_path, name)
        with open(filename, 'wb') as f:
            f.write(image)
        logging.info(filename + ' created')

        filename, w, h = base_res.resize_image(filename, height=height)
        return filename.replace(self.application.BASE_DIR, ''), w, h

    @staticmethod
    def save(self, bid, block_type, content):
        block = dict(content=content)
        try:
            if bid == 'new':
                block['update_time'] = block['create_time'] = datetime.now()
                block['create_user'] = block.get('create_user', self.current_user.id)
                r = self.db.block.insert_one(block)
                bid = block['id'] = str(r.inserted_id)
                if len(content) > 10:
                    self.add_op_log(None, 'add_block', file_id=bid, context='%s:%d' % (block_type, len(content)))
            else:
                r = self.db.block.update_one({'_id': ObjectId(bid)}, {'$set': block})
                if not r.matched_count:
                    return self.send_error(errors.no_object)
                if r.modified_count:
                    block['update_time'] = datetime.now()
                    self.db.block.update_one({'_id': ObjectId(bid)}, {'$set': {'update_time': block['update_time']}})
                    self.add_op_log(None, 'save_block', file_id=bid, context='%s:%d' % (block_type, len(content)))
            return [bid, convert_bson(block).get('update_time'), block.get('create_user', '')]

        except db_errors as e:
            return self.send_db_error(e)


class AskCloneHandler(BaseHandler):
    URL = '/api/res/clone/(\w{24})'

    @authenticated
    def post(self, rid):
        """ 申请改编资源 """
        try:
            item = convert_bson(self.db.res.find_one(dict(create_user=self.current_user.id, source=rid)))
            if item:
                return self.send_response({'id': item['id']})

            item = convert_bson(self.db.res.find_one({'_id': ObjectId(rid)}))
            if not item:
                return self.send_error(errors.no_object)
            if item.get('clone_auth') == 'deny':
                return self.send_error(errors.unauthorized, reason='作者已设置为不允许改编此资源')

            item['source_user'] = item['create_user']
            item['source'] = rid
            item['source_author'] = item['author']
            item['create_user'] = self.current_user.id
            item['author'] = self.current_user.name
            item['update_time'] = item['create_time'] = datetime.now()
            if not item['title'].endswith('(改编)'):
                item['title'] += '(改编)'
            item.pop('id', 0)
            item.pop('published', 0)

            for block in item['blocks']:
                block['origin'] = block['id']

            r = self.db.res.insert_one(item)
            item['id'] = str(r.inserted_id)
            self.add_op_log(None, 'clone_res', file_id=item['id'],
                            context='source %s, %s' % (item['source'], item['title']))
            self.send_response({'id': item['id']})
        except db_errors as e:
            return self.send_db_error(e)
