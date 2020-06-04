#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/22
"""
import re
import uuid
import mimetypes
from datetime import datetime
from tests.users import admin
from bson import json_util
from bson.objectid import ObjectId
from tornado.util import PY3
from functools import partial
from tornado.options import options
from tornado.escape import json_encode
from tornado.httpclient import HTTPRequest
from tornado.testing import AsyncHTTPTestCase
from tornado.escape import to_basestring, native_str
import controller as c
from controller import auth
from controller import helper as h
from controller.app import Application
from controller.page.base import PageHandler as Ph

if PY3:
    import http.cookies as Cookie
else:
    import Cookie

cookie = Cookie.SimpleCookie()


# https://github.com/ooclab/ga.service/blob/master/src/codebase/utils/fetch_with_form.py
def body_producer(boundary, files, params, write):
    boundary_bytes = boundary.encode()
    crlf = b'\r\n'

    for arg_name in files:
        filename = files[arg_name]
        filename_bytes = filename.encode()
        write(b'--%s%s' % (boundary_bytes, crlf))
        write(b'Content-Disposition: form-data; name="%s"; filename="%s"%s' %
              (arg_name.encode(), filename_bytes, crlf))

        m_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        write(b'Content-Type: %s%s' % (m_type.encode(), crlf))
        write(crlf)
        with open(filename, 'rb') as f:
            while True:
                # 16k at a time.
                chunk = f.read(16 * 1024)
                if not chunk:
                    break
                write(chunk)

        write(crlf)

    for arg_name in params:
        value = str(params[arg_name])
        write(b'--%s%s' % (boundary_bytes, crlf))
        write(b'Content-Disposition: form-data; name="%s"{}{}%s{}'.replace(b'{}', crlf) %
              (arg_name.encode(), value.encode()))

    write(b'--%s--%s' % (boundary_bytes, crlf))


class APITestCase(AsyncHTTPTestCase):

    def get_app(self, testing=True, debug=False):
        options.debug = debug
        options.testing = testing
        options.port = self.get_http_port()
        return Application(c.handlers + c.views, db_name_ext='_test', ui_modules=c.modules,
                           default_handler_class=c.InvalidPageHandler)

    def tearDown(self):
        super(APITestCase, self).tearDown()
        self._app.stop()

    @staticmethod
    def parse_response(response):
        body = response.body and to_basestring(response.body) or '{}'
        if body and body.startswith('{'):
            body = json_util.loads(body)
            if 'data' in body and isinstance(body['data'], dict):  # 将data的内容赋给body，以便测试使用
                body.update(body['data'])
            elif 'error' in body and isinstance(body['error'], dict):
                body.update(body['error'])
        if response.code != 200 and 'code' not in body:
            body = dict(code=response.code, message=response.reason)
        return body

    def get_code(self, response):
        response = self.parse_response(response)
        return isinstance(response, dict) and response.get('code')

    def assert_code(self, code, response, msg=None):
        """
        判断response中是否存在code
        :param code: 有三种类型：code; (code, message); [(code, message), (code, message)...]
        :param response: 请求的响应体
        """
        code = code[0] if isinstance(code, tuple) else code
        r_code = self.get_code(response) if self.get_code(response) else response.code
        if isinstance(code, list):
            self.assertIn(r_code, [c[0] if isinstance(c, tuple) else c for c in code], msg=msg)
        else:
            self.assertEqual(code, r_code, msg=msg)

    def fetch(self, url, **kwargs):
        files = kwargs.pop('files', None)  # files包含字段名和文件名，例如 files={'img': img_path}
        if isinstance(kwargs.get('body'), dict):
            if not files:
                kwargs['body'] = json_util.dumps(kwargs['body'])
            elif 'data' in kwargs['body']:  # 可以同时指定files和body={'data': {...}}，在API内取 self.get_request_data()
                kwargs['body']['data'] = json_util.dumps(kwargs['body']['data'])
        if 'body' in kwargs or files:
            kwargs['method'] = kwargs.get('method', 'POST')

        headers = kwargs.get('headers', {})
        headers['Cookie'] = ''.join(['%s=%s;' % (x, morsel.value) for (x, morsel) in cookie.items()])

        url = url if re.match('^http', url) else self.get_url(url)
        if files:
            boundary = uuid.uuid4().hex
            headers.update({'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
            producer = partial(body_producer, boundary, files, kwargs.pop('body', {}))
            request = HTTPRequest(url, headers=headers, body_producer=producer, **kwargs)
        else:
            request = HTTPRequest(url, headers=headers, **kwargs)

        self.http_client.fetch(request, self.stop)

        response = self.wait(timeout=60)
        headers = response.headers
        try:
            sc = headers._dict.get('Set-Cookie') if hasattr(headers, '_dict') else headers.get('Set-Cookie')
            if sc:
                text = native_str(sc)
                text = re.sub(r'Path=/(,)?', '', text)
                cookie.update(Cookie.SimpleCookie(text))
                while True:
                    cookie.update(Cookie.SimpleCookie(text))
                    if ',' not in text:
                        break
                    text = text[text.find(',') + 1:]
        except KeyError:
            pass

        return response

    def login(self, email, password):
        return self.fetch('/api/user/login', body={'data': dict(phone_or_email=email, password=password)})

    def login_as_admin(self):
        return self.login(admin[0], admin[1])

    def register_and_login(self, info):
        """ 先用info信息登录，如果成功则返回，如果失败则用info注册。用户注册后，系统会按注册信息自动登录。 """
        r = self.fetch('/api/user/login', body={'data': dict(phone_or_email=info['email'], password=info['password'])})
        return r if self.get_code(r) == 200 else self.fetch('/api/user/register', body={'data': info})

    def add_users_by_admin(self, users, roles=None):
        """ 以管理员身份新增users所代表的用户并授予权限，完成后当前用户为管理员 """
        self.register_and_login(dict(email=admin[0], password=admin[1], name=admin[2]))
        for u in users:
            r = self.register_and_login(u)
            self.assert_code(200, r)
            data = self.parse_response(r)
            u['_id'] = data.get('_id')
        self.assert_code(200, self.login_as_admin())
        if roles:
            for u in users:
                u['roles'] = u.get('roles', roles)
                r = self.fetch('/api/user/role', body={'data': dict(_id=u['_id'], roles=u['roles'])})
                self.assert_code(200, r)
        return users

    def add_first_user_as_admin_then_login(self):
        """
        创建第一个用户，作为超级管理员，并且登录。
        在创建其他用户前先创建管理员，避免测试用例乱序执行引发错误。
        """
        self._app.db.user.drop()
        r = self.register_and_login(dict(email=admin[0], password=admin[1], name=admin[2]))
        self.assert_code(200, r)
        u = self.parse_response(r)
        r = self.fetch('/api/user/role',
                       body={'data': dict(_id=u['_id'], roles=','.join(auth.get_assignable_roles()))})
        self.assert_code(200, r)
        return r

    def assert_status(self, pages, response, task2status, msg=None):
        for task_type, status in task2status.items():
            data = response.get('data', {})
            _pages = data.get(status, []) or data.get(task_type, {}).get(status, [])
            self.assertEqual(set(pages), set(_pages), msg=msg)

    @staticmethod
    def set_pub_data(data):
        assert data.get('task_type')
        task_type = data['task_type']
        steps = h.prop(Ph.task_types, task_type + '.steps')
        pre_tasks = h.prop(Ph.task_types, task_type + '.pre_tasks')
        data['num'] = data.get('num', 1)
        data['force'] = data.get('force', '0')
        data['priority'] = data.get('priority', 2)
        data['batch'] = data.get('batch', '测试批次号')
        data['steps'] = data.get('steps') or (steps and [s[0] for s in steps])
        data['pre_tasks'] = data.get('pre_tasks') if 'pre_tasks' in data else pre_tasks
        return data

    def publish_page_tasks(self, data):
        return self.fetch('/api/page/task/publish', body={'data': self.set_pub_data(data)})

    def finish_task(self, task_id):
        return self.fetch('/api/task/finish/' + str(task_id), body={'data': {}})

    def reset_tasks_and_data(self):
        """ 重置任务以及数据 """
        self._app.db.task.delete_many({})
        self._app.db.char.update_many({}, {'$unset': {'txt_level': '', 'txt_logs': ''}})
        self._app.db.page.update_many(
            {'$or': [{'chars.box_level': {'$exists': True}}, {'chars.box_logs': {'$exists': True}}]},
            {'$unset': {'chars.box_level': '', 'chars.box_logs': ''}}
        )
