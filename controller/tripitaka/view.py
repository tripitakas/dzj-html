#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 如是藏经、实体藏经
@time: 2019/3/13
"""
from functools import cmp_to_key
import controller.errors as errors
from controller.base import BaseHandler


class RsTripitakaHandler(BaseHandler):
    URL = '/tripitaka/rs'

    def get(self):
        """ 如是藏经 """
        self.render('tripitaka_rs.html')


class TripitakaListHandler(BaseHandler):
    URL = '/tripitaka'

    def get(self):
        """ 藏经列表 """
        self.render('tripitaka_list.html')


class TripitakaHandler(BaseHandler):
    URL = '/tripitaka/@page_name'

    def get(self, page_name='YB_1_1'):
        """ 实体藏经 """
        # OSS上有图片的藏经
        try:
            name_slice = page_name.split('_')
            tripitaka = name_slice[0]
            if tripitaka not in ['GL', 'LC', 'JX', 'FS', 'HW', 'QD', 'PL', 'QS', 'SX', 'YB', 'ZH', 'QL']:
                self.send_error_response(errors.tripitaka_not_existed)

            meta = self.db.tripitaka.find_one({'tripitaka_code': tripitaka})
            store_rules = meta.get('store_rules')
            if '册' in store_rules:
                mulu_info = list(self.db.volume.find(
                    {'tripitaka_code': tripitaka},
                    {'name': 1, 'envelop_num': 1, 'volume_num': 1, 'content_page_count': 1, '_id': 0},
                ))
            else:
                mulu_info = list(self.db.sutra.find(
                    {'sutra_code': {'$regex': '%s.*' % tripitaka}},
                    {'sutra_code': 1, 'sutra_name': 1, 'due_reel_count': 1, '_id': 0},
                ))
            mulu_info = self.format_mulu(mulu_info, store_rules)

            cur_page, cur_juan_or_volume_code = int(name_slice[-2]), '_'.join(name_slice[:-1])
            cur_mulu, page_count = {}, None
            for m in mulu_info:
                if m['code'] == cur_juan_or_volume_code:
                    cur_mulu, page_count = m, m.get('page_count')
            img_url = self.get_img(page_name)
            self.render('tripitaka.html', meta=meta, store_rules=store_rules, mulu_info=mulu_info, cur_page=cur_page,
                        cur_mulu=cur_mulu, page_count=page_count, img_url=img_url)

        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def format_mulu(mulu_info, store_rules):
        """ 格式化目录信息 """

        def get_title(envelop_num, volume_num):
            title = '第%s册' % volume_num
            if envelop_num:
                title = '第%s函/' % envelop_num + title
            return title

        def cmp_mulu(a, b):
            al, bl = a.get('code').split('-'), b.get('code').split('-')
            if len(al) != len(bl):
                return len(al) - len(bl)
            for i in range(len(al)):
                length = max(len(al[i]), len(bl[i]))
                ai, bi = al[i].zfill(length), bl[i].zfill(length)
                if ai != bi:
                    return 1 if ai > bi else -1
            return 0

        if '册' in store_rules:
            mulu = []
            for item in mulu_info:
                info = dict(
                    title=get_title(item.get('envelop_num'), item.get('volume_num')),
                    code=item['name'], page_count=item['content_page_count']
                )
                mulu.append(info)
        else:
            mulu = [dict(
                title=item['sutra_name'],
                code=item['sutra_code'], page_count=item['due_reel_count'],
            ) for item in mulu_info]

        mulu.sort(key=cmp_to_key(cmp_mulu))

        return mulu
