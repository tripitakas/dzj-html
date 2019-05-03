#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: Handler基类
@time: 2018/6/23
"""

import re
import logging
import traceback
import hashlib

from bson.errors import BSONError
from pymongo.errors import PyMongoError
from tornado import gen
from tornado.escape import json_decode, to_basestring
from tornado.httpclient import AsyncHTTPClient
from tornado.options import options
from tornado.web import RequestHandler
from tornado_cors import CorsMixin
from bson import json_util

from controller import errors
from controller.role import get_route_roles, can_access
from controller.helper import get_date_time

MongoError = (PyMongoError, BSONError)
DbError = MongoError


class BaseHandler(CorsMixin, RequestHandler):
    """ 后端API响应类的基类 """
    CORS_HEADERS = 'Content-Type,Host,X-Forwarded-For,X-Requested-With,User-Agent,Cache-Control,Cookies,Set-Cookie'
    CORS_CREDENTIALS = True

    def initialize(self):
        self.db = self.application.db

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*' if options.debug else self.application.site['domain'])
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Access-Control-Allow-Headers', self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self._get_methods())
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def prepare(self):
        """ 调用 get/post 前的准备 """

        # 检查是否单元测试用户、访客可以访问
        open_roles = '单元测试用户, 访客' if options.testing else '访客'
        if can_access(open_roles, self.request.path, self.request.method):
            return

        # 检查用户是否已登录
        is_api = '/api/' in self.request.path
        if not self.current_user:
            return self.send_error(errors.need_login, reason='需要重新登录') if is_api \
                else self.redirect(self.get_login_url())

        # 检查数据库中是否有该用户
        user_in_db = self.db.user.find_one(dict(email=self.current_user['email']))
        if not user_in_db:
            return self.send_error(errors.no_user, reason='需要重新注册') if is_api \
                else self.redirect(self.get_login_url())

        # 检查前更新roles
        self.current_user['roles'] = user_in_db.get('roles', '')
        self.set_secure_cookie('user', json_util.dumps(self.current_user))

        # 检查是否不需授权（即普通用户可访问，或单元测试中传入_no_auth=1）
        if can_access('普通用户', self.request.path, self.request.method):
            return

        # 单元测试时，跳过权限检查
        if self.get_query_argument('_no_auth', 0) == '1' and options.testing:
            return

        # 检查当前用户是否可以访问本请求
        if can_access(self.current_user['roles'], self.request.path, self.request.method):
            return
        else:
            need_roles = get_route_roles(self.request.path, self.request.method)
            if options.debug or options.testing:  # TODO: 正式上线时去掉本行或加上 or 1
                self.send_error(errors.unauthorized, render=not is_api, reason=','.join(need_roles))

    def get_current_user(self):
        if 'Access-Control-Allow-Origin' not in self._headers:
            self.write({'code': 403, 'error': 'Forbidden'})
            return self.finish()

        user = self.get_secure_cookie('user')
        try:
            return user and json_util.loads(user) or None
        except TypeError as e:
            print(user, str(e))


    def render(self, template_name, **kwargs):
        kwargs['currentRoles'] = self.current_user and self.current_user.get('roles') or ''
        kwargs['currentUserId'] = self.current_user['id'] if self.current_user else ''
        kwargs['protocol'] = self.request.protocol
        kwargs['debug'] = self.application.settings['debug']
        kwargs['site'] = dict(self.application.site)
        kwargs['current_url'] = self.request.path

        # 单元测试时，获取传递给页面的数据
        if self.get_query_argument('_raw', 0) == '1':
            kwargs = dict(kwargs)
            for k, v in list(kwargs.items()):
                if hasattr(v, '__call__'):
                    del kwargs[k]
            return self.send_response(kwargs)

        logging.info(template_name + ' by class ' + self.__class__.__name__)

        try:
            super(BaseHandler, self).render(template_name, dumps=json_util.dumps, **kwargs)  # dumps用于模板中解析数据
        except Exception as e:
            kwargs.update(dict(code=500, error='网页生成出错: %s' % (str(e))))
            super(BaseHandler, self).render('_error.html', **kwargs)

    def get_request_data(self):
        """
        获取请求数据。
        客户端请求需在请求体中包含 data 属性，例如 $.ajax({url: url, data: {data: some_obj}...
        """
        if 'data' not in self.request.body_arguments:
            body = json_decode(self.request.body).get('data')
        else:
            body = self.get_body_argument('data')

        try:
            return json_decode(body or '{}')
        except ValueError:
            logging.error(body)

    def send_response(self, response=None):
        """ 发送API响应内容，结束处理 """
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        if not response:
            response = {'status': 'success'}
        if isinstance(response, list):
            response = {'status': 'success', 'items': response}
        self.write(json_util.dumps(response))
        self.finish()

    def send_error(self, status_code=500, error=None, render=False, **kwargs):
        """
        发送异常响应消息，结束处理
        :param status_code: 错误码，系统调用时会传此参数
        :param error: 错误消息。如果类型为tuple，则表示为单个错误；如果类型为dict，则表示为多个错误。
        :param render: render为False，表示ajax请求，则返回json数据；为True，表示页面请求，则返回错误页面。
        """
        error = error or (status_code if isinstance(status_code, tuple) else
                          (status_code, kwargs.get('reason', '后台服务出错')))
        assert type(error) in [tuple, dict]
        response = {'status': 'failed', 'error': {}}
        if isinstance(error, tuple):
            status_code, message = error
            if 'reason' in kwargs and kwargs['reason'] != message:
                message += ': ' + kwargs['reason']
            kwargs['reason'] = message
            response['error'] = {'': (status_code, message)}
        elif isinstance(error, dict):
            response['error'] = error

        if render:
            return self.render('_error.html', code=status_code, error=kwargs.get('reason', '后台服务出错'))
        self.write_error(status_code, response, **kwargs)

    def write_error(self, status_code, response=None, **kwargs):
        """ 发送API异常响应消息，结束处理 """
        reason = kwargs.get('reason') or self._reason
        reason = reason if reason != 'OK' else '无权访问' if status_code == 403 else '后台服务出错 (%s, %s)' % (
            str(self).split('.')[-1].split(' ')[0],
            str(kwargs.get('exc_info', (0, '', 0))[1]))
        logging.error('%d %s [%s %s]' % (status_code, reason,
                                         self.current_user and self.current_user['name'], self.get_ip()))
        if not self._finished:
            self.send_response(response)


    def send_db_error(self, e, render=False):
        code = type(e.args) == tuple and len(e.args) > 1 and e.args[0] or 0
        reason = re.sub(r'[<{;:].+$', '', e.args[1]) if code else re.sub(r'\(0.+$', '', str(e))
        if not code and '[Errno' in reason and isinstance(e, MongoError):
            code = int(re.sub(r'^.+Errno |\].+$', '', reason))
            reason = re.sub(r'^.+\]', '', reason)
            return self.send_error(errors.mongo_error[0] + code,
                                   render=render,
                                   reason='无法访问文档库' if code in [61] else '%s(%s)%s' % (
                                       errors.mongo_error[1], e.__class__.__name__, ': ' + (reason or '')))
        if code:
            logging.error(e.args[1])
        if 'InvalidId' == e.__class__.__name__:
            code, reason = 1, errors.no_object[1]
        if code not in [2003, 1]:
            traceback.print_exc()
        default_error = errors.mongo_error if isinstance(e, MongoError) else errors.db_error
        self.send_error(default_error[0] + code, for_yield=True,
                        render=render,
                        reason='无法连接数据库' if code in [2003] else '%s(%s)%s' % (
                            default_error[1], e.__class__.__name__, ': ' + (reason or '')))

    def get_ip(self):
        ip = self.request.headers.get('x-forwarded-for') or self.request.remote_ip
        return ip and re.sub(r'^::\d$', '', ip[:15]) or '127.0.0.1'

    def add_op_log(self, op_type, file_id=None, context=None):
        logging.info('%s,file_id=%s,context=%s' % (op_type, file_id, context))
        self.db.log.insert_one(dict(type=op_type,
                                    user_id=self.current_user and self.current_user['id'],
                                    file_id=file_id or None,
                                    context=context and context[:80],
                                    create_time=get_date_time(),
                                    ip=self.get_ip()))

    def get_img_url(self, page_code):
        host = self.application.config['img']['host']
        salt = self.application.config['img']['salt']
        md5 = hashlib.md5()
        md5.update((page_code + salt).encode('utf-8'))
        hash_value = md5.hexdigest()
        inner_path = '/'.join(page_code.split('_')[:-1])
        return '%s/pages/%s/%s_%s.jpg' % (host, inner_path, page_code, hash_value)

    @gen.coroutine
    def call_back_api(self, url, handle_response, handle_error=None, **kwargs):
        self._auto_finish = False
        client = AsyncHTTPClient()
        url = re.sub('[\'"]', '', url)
        if not re.match(r'http(s)?://', url):
            url = '%s://localhost:%d%s' % (self.request.protocol, options['port'], url)
            r = yield client.fetch(url, headers=self.request.headers, validate_cert=False, **kwargs)
        else:
            r = yield client.fetch(url, validate_cert=False, **kwargs)
        if r.error:
            if handle_error:
                handle_error(r.error)
            else:
                self.render('_error.html', code=500, error='错误1: ' + r.error)
        else:
            try:
                try:
                    body = str(r.body, encoding='utf-8').strip()
                except UnicodeDecodeError:
                    body = str(r.body, encoding='gb18030').strip()
                except TypeError:
                    body = to_basestring(r.body).strip()
                self._handle_body(body, handle_response, handle_error)
            except Exception as e:
                e = '错误(%s): %s' % (e.__class__.__name__, str(e))
                if handle_error:
                    handle_error(e)
                else:
                    self.render('_error.html', code=500, error=e)

    def _handle_body(self, body, handle_response, handle_error):
        if re.match(r'(\s|\n)*(<!DOCTYPE|<html)', body, re.I):
            if 'var next' in body:
                body = re.sub(r"var next\s?=\s?.+;", "var next='%s';" % self.request.path, body)
                body = re.sub(r'\?next=/.+"', '?next=%s"' % self.request.path, body)
                self.write(body)
                self.finish()
            else:
                handle_response(body)
        else:
            body = json_decode(body)
            if body.get('error'):
                if handle_error:
                    handle_error(body['error'])
                else:
                    self.render('_error.html', code=500, error='错误3: ' + body['error'])
            else:
                handle_response(body)
