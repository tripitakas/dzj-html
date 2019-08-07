#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 如是藏经、实体藏经
@time: 2019/3/13
"""
import re
from functools import cmp_to_key
import controller.errors as errors
from controller.base import BaseHandler


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka'

    def get(self):
        """ 藏经列表 """
        try:
            self.render('tripitaka_list.html', items=list(self.db.tripitaka.find({})))
        except Exception as e:
            self.send_db_error(e, render=True)


class RsTripitakaHandler(BaseHandler):
    URL = '/tripitaka/rs'

    def get(self):
        """ 如是藏经 """
        self.render('tripitaka_rs.html')


class TripitakaHandler(BaseHandler):
    URL = ['/t/@tripitaka/@page_num', '/t/@tripitaka']

    def get(self, tripitaka='GL', page_num=''):
        """ 实体藏经 """
        try:
            meta = self.db.tripitaka.find_one({'tripitaka_code': tripitaka}) or {}
            if not meta:
                self.send_error_response(errors.tripitaka_not_existed, render=True)
            elif meta.get('img_available') == '否':
                pass  # self.send_error_response(errors.tripitaka_img_not_existed, render=True)

            store_pattern = meta.get('store_pattern')

            # 根据存储结构补齐page_num
            name_slice = page_num.split('_') if page_num else []
            gap_length = len(store_pattern.split('_')) - len(name_slice) - 1
            for i in range(gap_length):
                name_slice.append('1')
            cur_page = name_slice[-1] if gap_length == 0 else None
            cur_mulu_code = tripitaka + '_' + '_'.join(name_slice[:-1])

            # 获取藏经目录
            if '册' in store_pattern:
                mulu_items = list(self.db.volume.find({'tripitaka_code': tripitaka}))
            else:
                mulu_items = list(self.db.reel.find({'name': {'$regex': '^%s.*' % tripitaka}}))
            mulu_tree = self.get_mulu_tree(mulu_items, store_pattern)

            # 获取当前目录
            if '册' in store_pattern:
                cur_mulu = self.db.volume.find_one({'name': cur_mulu_code}) or {}
                first, last = int(cur_mulu.get('first_page', 1)), int(cur_mulu.get('last_page', 0))
                cur_page = int(cur_page) if cur_page else first
                nav_info = dict(parent_id=cur_mulu_code, cur_page=cur_page, first=first, last=last,
                                prev=cur_page - 1 or 1, next=cur_page + 1 if cur_page < last else last)
            else:
                cur_mulu = self.db.reel.find_one({'name': cur_mulu_code}) or {}
                first, last = 1, int(cur_mulu.get('page_count', 0))
                cur_page = first if not cur_page else int(cur_page)
                nav_info = dict(parent_id=cur_mulu_code, first=first, last=last, cur_page=cur_page,
                                prev=cur_page - 1 or 1, next=cur_page + 1 if cur_page < last else last)

            # 是否存在经目数据
            has_meta = True if self.db.sutra.find_one({'name': {'$regex': '^%s.*' % tripitaka}}) else False

            # 获取图片路径
            page_code = '%s_%s' % (nav_info['parent_id'], cur_page)
            img_url = self.get_img(page_code)

            # 是否存在文本数据
            page = self.db.page.find_one({'name': page_code})
            has_text = False
            if page and (page.get('text') or page.get('ocr')):
                has_text = True

            self.render('tripitaka.html', tripitaka=tripitaka, meta=meta, mulu_tree=mulu_tree, nav_info=nav_info,
                        img_url=img_url, has_meta=has_meta, has_text=has_text)

        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def get_mulu_tree(mulu_items, store_pattern):
        """ 获取目录信息 """

        def get_title(item, field='volume_num'):
            maps = {'envelop_num': '函', 'volume_num': '册', 'reel_num': '卷'}
            return '第%s%s' % (item.get(field), maps.get(field))

        def get_parent_id(id):
            return '_'.join(id.split('_')[:-1])

        def cmp_mulu(a, b):
            al, bl = a.get('id').split('-'), b.get('id').split('-')
            if len(al) != len(bl):
                return len(al) - len(bl)
            for i in range(len(al)):
                length = max(len(al[i]), len(bl[i]))
                ai, bi = al[i].zfill(length), bl[i].zfill(length)
                if ai != bi:
                    return 1 if ai > bi else -1
            return 0

        if '函' in store_pattern:
            mulu_tree = {get_parent_id(item['name']): dict(
                id=get_parent_id(item['name']), title=get_title(item, field='envelop_num'), children=[],
            ) for item in mulu_items}
            children = [dict(id=item['name'], title=get_title(item), page_count=item['content_page_count'],
                             parent_id=get_parent_id(item['name']), front_cover_count=item.get('front_cover_count'),
                             back_cover_count=item.get('back_cover_count')) for item in mulu_items]
            children.sort(key=cmp_to_key(cmp_mulu))
            for child in children:
                mulu_tree[child['parent_id']]['children'].append(child)
        elif '册' in store_pattern:
            mulu_tree = {item['name']: dict(
                id=item['name'], title=get_title(item), page_count=item['content_page_count'], children=[],
                front_cover_count=item.get('front_cover_count'), back_cover_count=item.get('back_cover_count')
            ) for item in mulu_items}
        else:
            mulu_tree = {item['sutra_code']: dict(
                id=item['sutra_code'], children=[],
                title='%s.%s' % (re.sub(r'[_a-zA-Z]+', '', item['sutra_code']), item['sutra_name']),
                front_cover_count=item.get('front_cover_count'), back_cover_count=item.get('back_cover_count'),
            ) for item in mulu_items}
            children = [dict(id=item['name'], title=get_title(item, 'reel_num'), page_count=item['page_count'],
                             parent_id=item['sutra_code']) for item in mulu_items]
            children.sort(key=cmp_to_key(cmp_mulu))
            for child in children:
                mulu_tree[child['parent_id']]['children'].append(child)

        mulu_tree = list(mulu_tree.values())
        mulu_tree.sort(key=cmp_to_key(cmp_mulu))

        return mulu_tree
