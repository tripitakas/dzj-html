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

from bson import json_util
from bson.errors import BSONError
from pymongo.errors import PyMongoError
from tornado import gen
from tornado.escape import to_basestring
from tornado.httpclient import AsyncHTTPClient
from tornado.options import options
from tornado.web import RequestHandler
from tornado_cors import CorsMixin

from controller import errors as e
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
        self.config = self.application.config

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*' if options.debug else self.application.site['domain'])
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Access-Control-Allow-Headers', self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self._get_methods())
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def prepare(self):
        """ 调用 get/post 前的准备 """
        p, m = self.request.path, self.request.method
        # 单元测试
        if options.testing and (self.get_query_argument('_no_auth', 0) == '1' or can_access('单元测试用户', p, m)):
            return
        # 检查是否访客可以访问
        if can_access('访客', p, m):
            return
        # 检查用户是否已登录
        api = '/api/' in p
        if not self.current_user:
            return self.send_error(e.need_login, reason='需要重新登录') if api else self.redirect(self.get_login_url())
        # 检查数据库中是否有该用户
        user_in_db = self.db.user.find_one(dict(_id=self.current_user.get('_id')))
        if not user_in_db:
            return self.send_error(e.no_user, reason='需要重新注册') if api else self.redirect(self.get_login_url())
        # 检查是否不需授权（即普通用户可访问）
        if can_access('普通用户', p, m):
            return
        # 检查当前用户是否可以访问本请求
        self.current_user['roles'] = user_in_db.get('roles', '')  # 检查权限前更新roles
        self.set_secure_cookie('user', json_util.dumps(self.current_user))
        if can_access(self.current_user['roles'], p, m):
            return
        # 报错，无权访问
        need_roles = get_route_roles(p, m)
        self.send_error(e.unauthorized, render=not api, reason=','.join(need_roles))

    def can_access(self, path, method='GET'):
        """检查当前用户是否能访问某个(path, method)"""
        role = self.current_user.get('roles')
        role = role if role else '普通用户'
        return can_access(role, path, method)

    def get_current_user(self):
        if 'Access-Control-Allow-Origin' not in self._headers:
            self.write({'code': 403, 'error': 'Forbidden'})
            return self.finish()

        user = self.get_secure_cookie('user')
        try:
            return user and json_util.loads(user) or None
        except TypeError as err:
            print(user, str(err))

    def render(self, template_name, **kwargs):
        kwargs['currentRoles'] = self.current_user and self.current_user.get('roles') or ''
        kwargs['currentUserId'] = self.current_user and self.current_user.get('_id') or ''
        kwargs['protocol'] = self.request.protocol
        kwargs['debug'] = self.application.settings['debug']
        kwargs['site'] = dict(self.application.site)
        kwargs['current_url'] = self.request.path
        # can_access/dumps/to_date_str传递给页面模板
        kwargs['can_access'] = self.can_access
        kwargs['dumps'] = json_util.dumps
        kwargs['to_date_str'] = lambda t, fmt='%Y-%m-%d %H:%M': t and t.strftime(fmt) or ''

        # 单元测试时，获取传递给页面的数据
        if self.get_query_argument('_raw', 0) == '1':
            return self.send_response({k: v for k, v in kwargs.items() if not hasattr(v, '__call__')})

        logging.info(template_name + ' by class ' + self.__class__.__name__)

        try:
            super(BaseHandler, self).render(template_name, **kwargs)
        except Exception as err:
            kwargs.update(dict(code=500, error='网页生成出错: %s' % (str(err) or err.__class__.__name__)))
            super(BaseHandler, self).render('_error.html', **kwargs)

    def get_request_data(self):
        """
        获取请求数据。
        客户端请求需在请求体中包含 data 属性，例如 $.ajax({url: url, data: {data: some_obj}...
        """
        if 'data' not in self.request.body_arguments:
            body = json_util.loads(self.request.body).get('data')
        else:
            body = json_util.loads(self.get_body_argument('data'))
        return body or {}

    def send_response(self, response=None, type='data', code=500, **kwargs):
        """
        发送API响应内容，并结束处理
        :param response: 返回给请求的内容。type为'error'时，如果response类型为tuple，表示单个错误，如果为dict，则表示多个错误
        :param type: 'data'表示正确数据，'error'表示错误消息
        :param code: 返回代码
        """
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

        assert type in ['data', 'error']
        if type == 'error' and isinstance(response, tuple):
            code = response[0]
        elif type == 'error' and isinstance(response, dict):
            if len(response) > 0 and isinstance(list(response.values())[0], tuple):
                first = list(response.values())[0]
                code = first[0]
        elif type == 'data':
            code = 200

        response = {'code': code, type: response}
        response.update(kwargs)
        self.write(json_util.dumps(response))
        self.finish()

    def send_error(self, status_code=500, render=False, **kwargs):
        """
        发送异常响应消息，并结束处理
        :param status_code: 错误代码，系统调用时会传此参数。重载后，status_code用来接受错误消息：
                            如果类型为tuple，则表示单个错误；如果类型为dict，则表示多个错误。
        :param render: render为False，表示ajax请求，则返回json数据；为True，表示页面请求，则返回错误页面。
        """
        error = status_code if type(status_code) in [tuple, dict] else None
        message, code_message = kwargs.get('message'), None
        if isinstance(status_code, tuple):
            status_code, code_message = error
        elif isinstance(status_code, dict):
            status_code, code_message = e.mutiple_errors
        kwargs['message'] = code_message if not message else message

        if render:
            return self.render('_error.html', code=status_code, message=kwargs['message'])

        self.write_error(status_code, error=error, **kwargs)

    def write_error(self, status_code=500, error=None, **kwargs):
        """ 发送API异常响应消息，结束处理 """
        message = kwargs.get('message') or self._reason
        message = message if message != 'OK' else '无权访问' if status_code == 403 else '后台服务出错 (%s, %s)' % (
            str(self).split('.')[-1].split(' ')[0],
            str(kwargs.get('exc_info', (0, '', 0))[1])
        )
        user_name = self.current_user and self.current_user['name']
        logging.error('%d %s [%s %s]' % (status_code, message, user_name, self.get_ip()))

        if not self._finished:
            self.send_response(response=error, type='error', **kwargs)

    def send_db_error(self, error, render=False):
        code = type(error.args) == tuple and len(error.args) > 1 and error.args[0] or 0
        reason = re.sub(r'[<{;:].+$', '', error.args[1]) if code else re.sub(r'\(0.+$', '', str(error))
        if not code and '[Errno' in reason and isinstance(error, MongoError):
            code = int(re.sub(r'^.+Errno |\].+$', '', reason))
            reason = re.sub(r'^.+\]', '', reason)
            return self.send_error(
                e.mongo_error[0] + code,
                render=render,
                reason='无法访问文档库' if code in [61] else '%s(%s)%s' % (
                    e.mongo_error[1], error.__class__.__name__, ': ' + (reason or ''))
            )

        if code:
            logging.error(error.args[1])
        if 'InvalidId' == error.__class__.__name__:
            code, reason = 1, e.no_object[1]
        if code not in [2003, 1]:
            traceback.print_exc()

        default_error = e.mongo_error if isinstance(error, MongoError) else e.db_error
        self.send_error(
            default_error[0] + code,
            for_yield=True,
            render=render,
            reason='无法连接数据库' if code in [2003] else '%s(%s)%s' % (
                default_error[1], error.__class__.__name__, ': ' + (reason or ''))
        )

    def get_ip(self):
        ip = self.request.headers.get('x-forwarded-for') or self.request.remote_ip
        return ip and re.sub(r'^::\d$', '', ip[:15]) or '127.0.0.1'

    def add_op_log(self, op_type, file_id=None, context=None):
        logging.info('%s,file_id=%s,context=%s' % (op_type, file_id, context))
        self.db.log.insert_one(dict(
            type=op_type,
            user_id=self.current_user and self.current_user.get('_id'),
            file_id=file_id or None,
            context=context and context[:80],
            create_time=get_date_time(),
            ip=self.get_ip()
        ))

    def get_img_url(self, page_code):
        host = self.config.get('img', {}).get('host')
        salt = self.config.get('img', {}).get('salt')
        md5 = hashlib.md5()
        md5.update((page_code + salt).encode('utf-8'))
        hash_value = md5.hexdigest()
        inner_path = '/'.join(page_code.split('_')[:-1])
        return '%s/pages/%s/%s_%s.jpg' % (host, inner_path, page_code, hash_value) if host and salt else ''

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
            except Exception as err:
                err = '错误(%s): %s' % (err.__class__.__name__, str(err))
                if handle_error:
                    handle_error(err)
                else:
                    self.render('_error.html', code=500, error=err)

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
            body = json_util.loads(body)
            if body.get('error'):
                if isinstance(body['error'], list):
                    error = body['error'][1]
                elif isinstance(body['error'], dict):
                    error = list(body['error'].values())[0][1]
                else:
                    error = body['error']

                if handle_error:
                    handle_error(error)
                else:
                    self.render('_error.html', code=500, error=error)
            else:
                handle_response(body.get('data') or body)
