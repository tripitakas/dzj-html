#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: Handler基类
@time: 2018/6/23
"""
import re
import logging
import traceback
from os import path
from bson import json_util
from bson.errors import BSONError
from pymongo.errors import PyMongoError
from datetime import datetime, timedelta
from tornado import gen
from tornado.web import Finish
from tornado_cors import CorsMixin
from tornado.options import options
from tornado.web import RequestHandler
from tornado.httpclient import HTTPError
from tornado.escape import to_basestring
from tornado.httpclient import AsyncHTTPClient
from controller import errors as e
from controller import validate as v
from controller.auth import get_route_roles, can_access, get_all_roles
from controller.helper import get_date_time, prop, md5_encode, gen_id, BASE_DIR


class BaseHandler(CorsMixin, RequestHandler):
    """ 后端API响应类的基类"""
    CORS_HEADERS = 'Content-Type,Host,X-Forwarded-For,X-Requested-With,User-Agent,Cache-Control,Cookies,Set-Cookie'
    CORS_CREDENTIALS = True

    MongoError = (PyMongoError, BSONError)
    DbError = MongoError

    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)
        self.db = self.application.db_test if self.get_query_argument('_test', 0) == '1' else self.application.db
        self.data = self.error = self.is_api = None
        self.user = self.user_id = self.username = None
        self.config = self.application.config
        self.more = {}  # 给子类使用

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*' if options.debug else self.application.site['domain'])
        self.set_header('Access-Control-Allow-Headers', self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self._get_methods())
        self.set_header('Access-Control-Allow-Credentials', 'true')
        self.set_header('Cache-Control', 'no-cache')

    def prepare(self):
        """ 调用 get/post 前的准备"""
        p, m = self.request.path, self.request.method
        self.is_api = '/api/' in p
        self.data = self.get_request_data() if self.is_api else {}
        # 单元测试
        if options.testing and (self.get_query_argument('_no_auth', 0) == '1' or can_access('单元测试用户', p, m)):
            return
        # 检查是否访客可以访问
        if can_access('访客', p, m):
            return
        # 检查是否直接登录
        if not self.current_user and self.data.get('login_id'):
            login_ids = self.prop(self.config, 'direct_login_id')
            if login_ids and self.data['login_id'] in login_ids:
                self.direct_login(self.data.get('login_id'), self.data.get('password'))
            else:
                return self.send_error_response(e.no_object, message='direct login id error')
        # 检查用户是否已登录
        login_url = self.get_login_url() + '?next=' + self.request.uri
        if not self.current_user:
            return self.send_error_response(e.need_login) if self.is_api else self.redirect(login_url)
        self.user_id, self.username = self.current_user.get('_id'), self.current_user.get('name')
        # 检查数据库中是否有该用户
        try:
            cond = [{f: self.current_user[f]} for f in ['email', 'phone'] if self.current_user.get(f)]
            user_in_db = self.db.user.find_one({'$or': cond} if cond else dict(_id=self.current_user.get('_id')))
            if not user_in_db:
                return self.send_error_response(e.no_user) if self.is_api else self.redirect(login_url)
        except self.MongoError as error:
            return self.send_db_error(error)
        # 检查是否不需授权（即普通用户可访问）
        if can_access('普通用户', p, m):
            return
        # 检查当前用户是否可以访问本请求
        self.current_user['roles'] = user_in_db.get('roles', '')  # 检查权限前更新roles
        self.set_secure_cookie('user', json_util.dumps(self.current_user), expires_days=2)
        if can_access(self.current_user['roles'], p, m):
            return
        # 检查URL是否配置
        need_roles = get_route_roles(p, m)
        if not need_roles:
            return self.send_error_response(e.url_not_config)
        # 报错，无权访问
        else:
            message = '无权访问，需要申请%s%s角色' % ('、'.join(need_roles), '中某一种' if len(need_roles) > 1 else '')
            return self.send_error_response(e.unauthorized, message=message)

    def direct_login(self, login_id, password):
        """ 直接登录，然后访问网站api"""
        # 检查是否多次登录失败
        if self.db.log.count_documents({'type': 'login-fail', 'content': login_id}) >= 12:
            self.db.user.update_one({'email': login_id}, {'$set': {'disabled': True}})
            return self.send_error_response(e.unauthorized, message='登录失败超过12次，账号被禁用，请联系管理员。')

        user = self.db.user.find_one({'email': login_id, 'disabled': {'$ne': True}})
        if not user:
            return self.send_error_response(e.no_user, message=e.no_user[1] + ' (%s)' % login_id)
        if gen_id(password) != user.get('password'):
            self.add_log('login_fail', content=login_id)
            return self.send_error_response(e.incorrect_password)

        # 清除登录失败记录
        self.db.log.delete_many({'type': 'login_fail', 'content': login_id})

        user['roles'] = user.get('roles', '')
        user['login_md5'] = gen_id(user['roles'])
        self.current_user = user
        self.set_secure_cookie('user', json_util.dumps(user), expires_days=2)
        self.add_log('login_ok', target_id=user['_id'], content='%s,%s,%s' % (user['name'], login_id, user['roles']))

    def can_access(self, req_path, method='GET'):
        """检查当前用户是否能访问某个(req_path, method)"""
        user_roles = '访客'
        if self.current_user:
            user_roles = '普通用户'
            if self.current_user.get('roles'):
                user_roles = get_all_roles(self.current_user['roles'])
        return can_access(user_roles, req_path, method)

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
        kwargs['prop'] = self.prop
        kwargs['dumps'] = json_util.dumps
        kwargs['to_date_str'] = lambda t, fmt='%Y-%m-%d %H:%M': get_date_time(fmt=fmt, date_time=t) if t else ''
        kwargs['file_exists'] = lambda fn: path.exists(path.join(self.application.BASE_DIR, fn))
        # check_auth 等处报错返回后就不再渲染
        if self._finished:
            return

        # 单元测试时，获取传递给页面的数据
        if self.get_query_argument('_raw', 0) == '1':
            kwargs = {k: v for k, v in kwargs.items() if not hasattr(v, '__call__') and k != 'error'}
            if template_name.startswith('_404') or template_name.startswith('_error'):
                return self.send_error_response((self.get_status(), self._reason), **kwargs)
            return self.send_data_response(**kwargs)

        logging.info(template_name + ' by ' + re.sub(r"^.+controller\.|'>", '', str(self.__class__)))
        # self.add_op_log('visit', context=self.request.path)

        try:
            super(BaseHandler, self).render(template_name, **kwargs)
        except Exception as error:
            traceback.print_exc()
            message = '网页生成出错(%s): %s' % (template_name, str(error) or error.__class__.__name__)
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
        if not body:
            body = dict(self.request.arguments)
            for k, s in body.items():
                body[k] = to_basestring(s[0])
        return body or {}

    def send_data_response(self, data=None, **kwargs):
        """
        发送正常响应内容，并结束处理
        :param data: 返回给请求的内容，字典或列表
        :param kwargs: 更多上下文参数
        :return: None
        """

        def remove_func(obj):
            if isinstance(obj, dict):
                for k, vo in list(obj.items()):
                    if callable(vo):
                        obj.pop(k)
                    remove_func(vo)
            elif isinstance(obj, list):
                for vo in obj:
                    remove_func(vo)

        assert data is None or isinstance(data, (list, dict))
        self.set_header('Content-Type', 'application/json; charset=UTF-8')

        r_type = 'multiple' if isinstance(data, list) else 'single' if isinstance(data, dict) else None
        response = dict(status='success', type=r_type, data=data or kwargs, code=200)
        response.update(kwargs)
        remove_func(response)
        self.write(json_util.dumps(response))
        self.finish()

    def send_error_response(self, error=None, **kwargs):
        """
        反馈错误消息，并结束处理
        :param error: 单一错误描述的元组(见errors.py)，或多个错误的字典对象
        :param kwargs: 错误的具体上下文参数，例如 message、render、page_name
        :return: None
        """
        self.error = error
        _type = 'multiple' if isinstance(error, dict) else 'single' if isinstance(error, tuple) else None
        _error = list(error.values())[0] if _type == 'multiple' else error
        code, message = _error
        # 如果kwargs中含有message，则覆盖error中对应的message
        message = kwargs['message'] if kwargs.get('message') else message

        response = dict(status='failed', type=_type, code=code, message=message, error=error)
        kwargs.pop('exc_info', 0)
        response.update(kwargs)

        render = not self.is_api and not self.get_query_argument('_raw', 0)
        if response.pop('render', render):  # 如果是页面渲染请求，则返回错误页面
            self.render('_error.html', **response)
            raise Finish()

        user_name = self.current_user and self.username
        class_name = re.sub(r"^.+controller\.|'>", '', str(self.__class__)).split('.')[-1]
        logging.error('%d %s in %s [%s %s]' % (code, message, class_name, user_name, self.get_ip()))

        if not self._finished:
            response.pop('exc_info', None)
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write(json_util.dumps(response))
            self.finish()
        raise Finish()

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

    def send_db_error(self, error):
        code = type(error.args) == tuple and len(error.args) > 1 and error.args[0] or 0
        if not isinstance(code, int):
            code = 0
        reason = re.sub(r'[<{;:].+$', '', str(error.args[1])) if code else re.sub(r'\(0.+$', '', str(error))
        if not code and '[Errno' in reason and isinstance(error, self.MongoError):
            code = int(re.sub(r'^.+Errno |\].+$', '', reason))
            reason = re.sub(r'^.+\]', '', reason)
            reason = '无法访问文档库' if code in [61] or 'Timeout' in error.__class__.__name__ else '%s(%s)%s' % (
                e.mongo_error[1], error.__class__.__name__, ': ' + (reason or '')
            )
            return self.send_error_response((e.mongo_error[0] + code, reason))

        if code:
            logging.error(error.args[1])
        if 'InvalidId' == error.__class__.__name__:
            code, reason = 1, e.no_object[1]
        if code not in [2003, 1]:
            traceback.print_exc()

        default_error = e.mongo_error if isinstance(error, self.MongoError) else e.db_error
        reason = '无法连接数据库' if code in [2003] else '%s(%s)%s' % (
            default_error[1], error.__class__.__name__, ': ' + (reason or '')
        )

        return self.send_error_response((default_error[0] + code, reason))

    @staticmethod
    def now():
        return datetime.now()

    @staticmethod
    def prop(obj, key, default=None):
        return prop(obj, key, default=default)

    def get_ip(self):
        ip = self.request.headers.get('x-forwarded-for') or self.request.remote_ip
        return ip and re.sub(r'^::\d$', '', ip[:15]) or '127.0.0.1'

    def get_config(self, key):
        return self.prop(self.config, key)

    def add_log(self, op_type, target_id=None, target_name=None, content=None, remark=None):
        logging.info('%s,username=%s,id=%s,context=%s' % (op_type, self.username, target_id, content))
        try:
            self.db.log.insert_one(dict(
                op_type=op_type, target_id=target_id, target_name=target_name, content=content,
                remark=remark, username=self.username, user_id=self.user_id,
                ip=self.get_ip(), create_time=self.now(),
            ))
        except self.MongoError:
            pass

    @classmethod
    def add_op_log(cls, db, op_type, status, content, username):
        """ 新增运维日志。运维日志指的是管理员的各种操作的日志记录"""
        assert status in ['ongoing', 'finished', '', None]
        try:
            r = db.oplog.insert_one(dict(
                op_type=op_type, status=status or None, content=content or [], create_by=username,
                create_time=cls.now(), updated_time=cls.now(),
            ))
            return r.inserted_id
        except cls.MongoError as error:
            print('错误(%s): %s' % (error.__class__.__name__, str(error)))
            pass

    def validate(self, data, rules):
        errs = v.validate(data, rules)
        errs and self.send_error_response(errs)

    def is_mod_enabled(self, mod):
        disabled_mods = self.prop(self.config, 'modules.disabled_mods')
        return not disabled_mods or mod not in disabled_mods

    def get_web_img(self, img_name, img_type='page', use_my_cloud=False):
        if not img_name:
            return ''
        inner_path = '/'.join(img_name.split('_')[:-1])
        if self.get_config('web_img.with_hash'):
            img_name += '_' + md5_encode(img_name, self.get_config('web_img.salt'))
        my_cloud = self.get_config('web_img.my_cloud')
        shared_cloud = self.get_config('web_img.shared_cloud')
        relative_url = '{0}s/{1}/{2}.jpg'.format(img_type, inner_path, img_name)
        # 从本地获取图片
        local_path = self.get_config('web_img.local_path')
        if local_path:
            img_url = '/{0}/{1}'.format(local_path.strip('/'), relative_url)
            if path.exists(path.join(BASE_DIR, img_url[1:])):
                return img_url
        # 从我的云盘获取图片。如果use_my_cloud为True，则返回我的云盘路径而不使用共享云盘
        if my_cloud and (img_type in (self.get_config('web_img.cloud_type') or '') or use_my_cloud):
            return path.join(my_cloud.replace('-internal', ''), relative_url)
        # 从共享盘获取图片
        if shared_cloud and img_type in (self.get_config('web_img.shared_type') or ''):
            return path.join(shared_cloud, relative_url)

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
                except Exception as error:
                    err = '错误(%s): %s' % (error.__class__.__name__, str(error))
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
