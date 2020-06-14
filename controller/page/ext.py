#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from .page import Page
from .base import PageHandler
from controller import errors as e
from controller import validate as v
from tornado.escape import native_str, url_escape


class PageTxtProofHandler(PageHandler):
    URL = '/page/txt_proof/@page_name'

    def get(self, page_name):
        """ 单字修改页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='页面%s不存在' % page_name)

            chars = page['chars']
            chars_col = self.get_chars_col(chars)
            char_dict = {c['cid']: c for c in chars}
            img_url = self.get_web_img(page['name'])
            readonly = '/edit' not in self.request.path
            txt_types = {'': '没问题', 'M': '模糊或残损', 'N': '不确定', '*': '不认识'}
            self.pack_boxes(page)
            self.render('page_txt_proof.html', page=page, chars=chars, chars_col=chars_col, char_dict=char_dict,
                        txt_types=txt_types, img_url=img_url, readonly=readonly)

        except Exception as error:
            return self.send_db_error(error)


class PageTextProofHandler(PageHandler):
    URL = '/page/text_proof/@page_name'

    def get(self, page_name):
        """ 文字校对页面"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            txts = self.get_txts(page)
            txt_dict = {t[1]: t for t in txts}
            doubts = [(self.prop(page, 'txt_doubt', ''), '校对存疑')]
            txt_fields = self.prop(page, 'txt_fields') or [t[1] for t in txts]
            cmp_data = self.prop(page, 'txt_html') or self.diff(*[t[0] for t in txts])
            img_url = self.get_web_img(page['name'], 'page')
            return self.render(
                'page_text_proof.html', page=page, img_url=img_url, txts=txts, txt_dict=txt_dict,
                txt_fields=txt_fields, cmp_data=cmp_data, doubts=doubts,
                active=None, readonly=True
            )

        except Exception as error:
            return self.send_db_error(error)


class PageDetectCharsApi(PageHandler):
    URL = '/api/page/txt/detect_chars'

    def post(self):
        """ 根据文本行内容识别宽字符"""
        try:
            mb4 = [[self.check_utf8mb4({}, t)['utf8mb4'] for t in s] for s in self.data['texts']]
            self.send_data_response(mb4)
        except Exception as error:
            return self.send_db_error(error)

    @classmethod
    def check_utf8mb4(cls, seg, base=None):
        column_strip = re.sub(r'\s', '', base or seg.get('base', ''))
        char_codes = [(c, url_escape(c)) for c in list(column_strip)]
        seg['utf8mb4'] = ','.join([c for c, es in char_codes if len(es) > 9])
        return seg


class PageTxtDiffApi(PageHandler):
    URL = '/api/page/txt/diff'

    def post(self):
        """ 用户提交纯文本后重新比较，并设置修改痕迹"""
        try:
            rules = [(v.not_empty, 'texts')]
            self.validate(self.data, rules)
            diff_blocks = self.diff(*self.data['texts'])
            if self.data.get('hints'):
                diff_blocks = self.set_hints(diff_blocks, self.data['hints'])
            cmp_data = self.render_string('_txt_diff.html', blocks=diff_blocks,
                                          sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))
            cmp_data = native_str(cmp_data)
            self.send_data_response(dict(cmp_data=cmp_data))

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def set_hints(diff_blocks, hints):
        for h in hints:
            line_segments = diff_blocks.get(h['block_no'], {}).get(h['line_no'])
            if not line_segments:
                continue
            for s in line_segments:
                if s['base'] == h['base'] and s['cmp1'] == h['cmp1']:
                    s['selected'] = True
        return diff_blocks
