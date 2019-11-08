#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: Handler基类
@time: 2018/6/23
"""

import re
import hashlib
import logging
import traceback

from os import path
from datetime import datetime

from bson import json_util
from bson.errors import BSONError
from pymongo.errors import PyMongoError
from tornado import gen
from tornado.escape import to_basestring
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPError
from tornado.options import options
from tornado.web import RequestHandler
from tornado_cors import CorsMixin

from controller import errors as e
from controller.auth import get_route_roles, can_access
from controller.helper import get_date_time
from controller.op_type import get_op_name

MongoError = (PyMongoError, BSONError)
DbError = MongoError


class BaseHandler(CorsMixin, RequestHandler):
    """ 后端API响应类的基类 """
    CORS_HEADERS = 'Content-Type,Host,X-Forwarded-For,X-Requested-With,User-Agent,Cache-Control,Cookies,Set-Cookie'
    CORS_CREDENTIALS = True

    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)
        self.db = self.application.db
        self.config = self.application.config
        self.more = {}  # 给子类记录使用

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
        login_url = self.get_login_url() + '?next=' + self.request.uri
        if not self.current_user:
            return self.send_error_response(e.need_login) if api else self.redirect(login_url)
        # 检查数据库中是否有该用户
        try:
            cond = [{f: self.current_user[f]} for f in ['email', 'phone'] if self.current_user.get(f)]
            user_in_db = self.db.user.find_one({'$or': cond} if cond else dict(_id=self.current_user.get('_id')))
            if not user_in_db:
                return self.send_error_response(e.no_user) if api else self.redirect(login_url)
        except MongoError as err:
            return self.send_db_error(err, render=not self.get_query_argument('_raw', 0) and not api)

        # 检查是否不需授权（即普通用户可访问）
        if can_access('普通用户', p, m):
            return
        # 检查当前用户是否可以访问本请求
        self.current_user['roles'] = user_in_db.get('roles', '')  # 检查权限前更新roles
        self.set_secure_cookie('user', json_util.dumps(self.current_user), expires_days=2)
        if can_access(self.current_user['roles'], p, m):
            return
        # 报错，无权访问
        need_roles = get_route_roles(p, m)
        if not need_roles:
            return self.send_error_response(e.url_not_found, render=not api)
        message = '无权访问，需要申请%s%s角色' % ('、'.join(need_roles), '中某一种' if len(need_roles) > 1 else '')
        return self.send_error_response(e.unauthorized, render=not api, message=message)

    def can_access(self, req_path, method='GET'):
        """检查当前用户是否能访问某个(req_path, method)"""
        role = '访客' if not self.current_user else self.current_user.get('roles') or '普通用户'
        return can_access(role, req_path, method)

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
        kwargs['debug'] = self.application.settings['debug']
        kwargs['site'] = dict(self.application.site)
        kwargs['current_path'] = self.request.path
        # can_access/dumps/to_date_str传递给页面模板
        kwargs['can_access'] = self.can_access
        kwargs['dumps'] = json_util.dumps
        kwargs['to_date_str'] = lambda t, fmt='%Y-%m-%d %H:%M': get_date_time(fmt=fmt, date_time=t)
        if self._finished:  # check_auth 等处报错返回后就不再渲染
            return

        # 单元测试时，获取传递给页面的数据
        if self.get_query_argument('_raw', 0) == '1':
            kwargs = {k: v for k, v in kwargs.items() if not hasattr(v, '__call__') and k != 'error'}
            if template_name.startswith('_404') or template_name.startswith('_error'):
                return self.send_error_response((self.get_status(), self._reason), **kwargs)
            return self.send_data_response(**kwargs)

        logging.info(template_name + ' by ' + re.sub(r"^.+controller\.|'>", '', str(self.__class__)))
        self.add_op_log('visit', context=self.request.path)

        try:
            super(BaseHandler, self).render(template_name, **kwargs)
        except Exception as err:
            traceback.print_exc()
            message = '网页生成出错(%s): %s' % (template_name, str(err) or err.__class__.__name__)
            kwargs.update(dict(code=500, message=message))
            super(BaseHandler, self).render('_error.html', **kwargs)

    def get_request_data(self):
        """
        获取请求数据。
        客户端请求需在请求体中包含 data 属性，例如 $.ajax({url: url, data: {data: some_obj}...
        """
        if 'data' not in self.request.body_arguments:
            body = b'{"data":' in self.request.body and json_util.loads(to_basestring(self.request.body)).get('data')
        else:
            body = json_util.loads(to_basestring(self.get_body_argument('data')))
        return body or {}

    def send_data_response(self, data=None, **kwargs):
        """
        发送正常响应内容，并结束处理
        :param data: 返回给请求的内容，字典或列表
        :param kwargs: 更多上下文参数
        :return: None
        """
        assert data is None or isinstance(data, (list, dict))
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

        r_type = 'multiple' if isinstance(data, list) else 'single' if isinstance(data, dict) else None
        response = dict(status='success', type=r_type, data=data, code=200)
        response.update(kwargs)
        self.write(json_util.dumps(response))
        self.finish()

    def send_error_response(self, error=None, **kwargs):
        """
        反馈错误消息，并结束处理
        :param error: 单一错误描述的元组(见errors.py)，或多个错误的字典对象
        :param kwargs: 错误的具体上下文参数，例如 message、render、page_name
        :return: None
        """
        _type = 'multiple' if isinstance(error, dict) else 'single' if isinstance(error, tuple) else None
        _error = list(error.values())[0] if _type == 'multiple' else error
        code, message = _error
        # 如果kwargs中含有message，则覆盖error中对应的message
        message = kwargs['message'] if kwargs.get('message') else message

        response = dict(status='failed', type=_type, code=code, message=message, error=error)
        kwargs.pop('exc_info', 0)
        response.update(kwargs)

        if response.pop('render', 0):  # 如果是页面渲染请求，则返回错误页面
            return self.render('_error.html', **response)

        user_name = self.current_user and self.current_user['name']
        class_name = re.sub(r"^.+controller\.|'>", '', str(self.__class__)).split('.')[-1]
        logging.error('%d %s in %s [%s %s]' % (code, message, class_name, user_name, self.get_ip()))

        if not self._finished:
            response.pop('exc_info', None)
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(json_util.dumps(response))
            self.finish()

    def send_error(self, status_code=500, **kwargs):
        """拦截系统错误，不允许API调用"""
        self.write_error(status_code, **kwargs)

    def write_error(self, status_code, **kwargs):
        """拦截系统错误，不允许API调用"""
        assert isinstance(status_code, int)
        message = kwargs.get('message') or kwargs.get('reason') or self._reason
        exc = kwargs.get('exc_info')
        exc = exc and len(exc) == 3 and exc[1]
        message = message if message != 'OK' else '无权访问' if status_code == 403 else '后台服务出错 (%s, %s)' % (
            str(self).split('.')[-1].split(' ')[0],
            '%s(%s)' % (exc.__class__.__name__, re.sub(r"^'|'$", '', str(exc)))
        )
        if re.search(r'\[Errno \d+\]', message):
            code = int(re.sub(r'^.+Errno |\].+$', '', message))
            message = re.sub(r'^.+\]', '', message)
            message = '无法访问文档库' if code in [61] else '%s: %s' % (e.mongo_error[1], message)
            return self.send_error_response((e.mongo_error[0] + code, message))
        return self.send_error_response((status_code, message), **kwargs)

    def send_db_error(self, error, render=False):
        code = type(error.args) == tuple and len(error.args) > 1 and error.args[0] or 0
        if not isinstance(code, int):
            code = 0
        reason = re.sub(r'[<{;:].+$', '', error.args[1]) if code else re.sub(r'\(0.+$', '', str(error))
        if not code and '[Errno' in reason and isinstance(error, MongoError):
            code = int(re.sub(r'^.+Errno |\].+$', '', reason))
            reason = re.sub(r'^.+\]', '', reason)
            reason = '无法访问文档库' if code in [61] or 'Timeout' in error.__class__.__name__ else '%s(%s)%s' % (
                e.mongo_error[1], error.__class__.__name__, ': ' + (reason or '')
            )
            return self.send_error_response((e.mongo_error[0] + code, reason), render=render)

        if code:
            logging.error(error.args[1])
        if 'InvalidId' == error.__class__.__name__:
            code, reason = 1, e.no_object[1]
        if code not in [2003, 1]:
            traceback.print_exc()

        default_error = e.mongo_error if isinstance(error, MongoError) else e.db_error
        reason = '无法连接数据库' if code in [2003] else '%s(%s)%s' % (
            default_error[1], error.__class__.__name__, ': ' + (reason or '')
        )

        return self.send_error_response((default_error[0] + code, reason), render=render)

    def get_ip(self):
        ip = self.request.headers.get('x-forwarded-for') or self.request.remote_ip
        return ip and re.sub(r'^::\d$', '', ip[:15]) or '127.0.0.1'

    def add_op_log(self, op_type, target_id=None, context=None, username=None):
        op_name = get_op_name(op_type)
        assert op_name, op_type + ' need add into op_type.py'
        username = username or self.current_user and self.current_user.get('name')
        user_id = self.current_user and self.current_user.get('_id')
        logging.info('%s,username=%s,target_id=%s,context=%s' % (op_type, username, target_id, context))
        try:
            self.db.log.insert_one(dict(
                op_type=op_type, username=username, user_id=user_id, target_id=target_id and str(target_id) or None,
                context=str(context), ip=self.get_ip(), create_time=datetime.now(),
            ))
        except MongoError:
            pass

    def get_img(self, page_code, resize=False, force_local=False):
        host = self.config.get('img', {}).get('host')
        salt = self.config.get('img', {}).get('salt')
        if not host or salt in [None, '', '待配置'] or force_local:
            fn = self.static_url('img/{0}/{1}.jpg'.format(page_code[:2], page_code))
            # fn = self.static_url('img/{0}/{1}.gif'.format('/'.join(page_code.split('_')[:-1]), page_code))
            if not path.exists(path.join(self.application.BASE_DIR, fn[1: fn.index('?')] if '?' in fn else fn[1:])):
                fn += '?err=1'  # cut.js 据此不显示图
            return fn
        md5 = hashlib.md5()
        md5.update((page_code + salt).encode('utf-8'))
        hash_value = md5.hexdigest()
        inner_path = '/'.join(page_code.split('_')[:-1])
        url = '%s/pages/%s/%s_%s.jpg' % (host, inner_path, page_code, hash_value)
        url = url + '?x-oss-process=image/resize,m_lfit,h_300,w_300' if resize else url
        return url

    @gen.coroutine
    def call_back_api(self, url, handle_response=None, handle_error=None, **kwargs):
        def callback(r):
            if r.error:
                if handle_error:
                    handle_error(str(r.error))
                else:
                    self.render('_error.html', code=500, message='错误1: ' + str(r.error))
            else:
                try:
                    if binary_response and r.body:
                        handle_response(r.body, **params_for_handler)
                    else:
                        try:
                            body = str(r.body, encoding='utf-8').strip()
                        except UnicodeDecodeError:
                            body = str(r.body, encoding='gb18030').strip()
                        except TypeError:
                            body = to_basestring(r.body).strip()
                        self._handle_body(body, params_for_handler, handle_response, handle_error)
                except Exception as err:
                    err = '错误(%s): %s' % (err.__class__.__name__, str(err))
                    traceback.print_exc()
                    if handle_error:
                        handle_error(err)
                    else:
                        self.render('_error.html', code=500, message=err)

        self._auto_finish = False
        kwargs['connect_timeout'] = kwargs.get('connect_timeout', 5)
        kwargs['request_timeout'] = kwargs.get('request_timeout', 5)
        binary_response = kwargs.pop('binary_response', False)
        params_for_handler = kwargs.pop('params', {})

        client = AsyncHTTPClient()
        url = re.sub('[\'"]', '', url)
        try:
            if not re.match(r'http(s)?://', url):
                url = '%s://localhost:%d%s' % (self.request.protocol, options['port'], url)
                yield client.fetch(url, headers=self.request.headers,
                                   callback=callback, validate_cert=False, **kwargs)
            else:
                yield client.fetch(url, callback=callback, validate_cert=False, **kwargs)
        except (OSError, HTTPError) as err_con:
            if handle_error:
                handle_error('服务无响应: ' + str(err_con))
            else:
                self.render('_error.html', code=500, message=str(err_con))

    def _handle_body(self, body, params_for_handler, handle_response, handle_error):
        if re.match(r'(\s|\n)*(<!DOCTYPE|<html)', body, re.I):
            if 'var next' in body:
                body = re.sub(r"var next\s?=\s?.+;", "var next='%s';" % self.request.path, body)
                body = re.sub(r'\?next=/.+"', '?next=%s"' % self.request.path, body)
                self.write(body)
                self.finish()
            else:
                handle_response(body, **params_for_handler)
        else:
            body = json_util.loads(body)
            if isinstance(body, dict) and body.get('error'):
                body['error'] = body.get('message') or body['error']
                if handle_error:
                    handle_error(body['error'])
                else:
                    self.render('_error.html', **body)
            else:
                handle_response(isinstance(body, dict) and body.get('data') or body, **params_for_handler)
