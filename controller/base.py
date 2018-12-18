#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 前端响应类的基础函数和类
@author: Zhang Yungui
@time: 2018/6/23
"""

from tornado.web import RequestHandler
from tornado.escape import to_basestring
from tornado import gen
from tornado_cors import CorsMixin
from tornado.httpclient import AsyncHTTPClient
from tornado.escape import json_decode, json_encode
import traceback
import re


class BaseHandler(CorsMixin, RequestHandler):
    """ 前端页面响应类的基类 """
    CORS_HEADERS = 'Content-Type,Host,X-Forwarded-For,X-Requested-With,User-Agent,Cache-Control,Cookies,Set-Cookie'
    CORS_CREDENTIALS = True

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Access-Control-Allow-Headers', self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self._get_methods())
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def get_current_user(self):
        user = self.get_secure_cookie('user')
        return user and json_decode(user) or None

    def render(self, template_name, **kwargs):
        kwargs['user'] = self.current_user or {}
        kwargs['authority'] = kwargs['user'].get('authority', '')
        kwargs['uri'] = self.request.uri
        kwargs['protocol'] = self.request.protocol
        kwargs['debug'] = self.application.settings['debug']
        kwargs['site'] = dict(self.application.site)

        super(BaseHandler, self).render(template_name, dumps=lambda p: json_encode(p), **kwargs)

    def render_error(self, code, error):
        if code != 404:
            traceback.print_exc()
        self.render('_404.html' if code == 404 else '_error.html', code=code, error=str(error))

    @gen.coroutine
    def call_back_api(self, url, handle_response):
        self._auto_finish = False
        client = AsyncHTTPClient()
        url = re.sub('[\'"]', '', url)
        if not re.match(r'http(s)?://', url):
            url = '%s://%s%s' % (self.request.protocol, self.application.site['url'], url)
            r = yield client.fetch(url, headers=self.request.headers, validate_cert=False)
        else:
            r = yield client.fetch(url, validate_cert=False)
        if r.error:
            self.render_error(r.code, r.error)
        else:
            try:
                try:
                    body = str(r.body, encoding='utf-8').strip()
                except UnicodeDecodeError:
                    body = str(r.body, encoding='gb18030').strip()
                if re.match('\S*(<!DOCTYPE|<html)', body, re.I):
                    if 'var next' in body:
                        body = re.sub(r"var next\s?=\s?.+;", "var next='%s';" % self.request.uri, body)
                        body = re.sub(r'\?next=/.+"', '?next=%s"' % self.request.uri, body)
                        self.write(body)
                        self.finish()
                    else:
                        handle_response(body)
                else:
                    body = json_decode(body)
                    if body.get('error'):
                        self.render_error(body.get('code', 500), body['error'])
                    else:
                        handle_response(body)
            except Exception as e:
                self.render_error(500, e)
