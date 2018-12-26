#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base import BaseHandler


class LoginHandler(BaseHandler):
    URL = ['/login', '/dzj_login.html']

    def get(self):
        """ 登录页面 """
        self.render('dzj_login.html', next=self.get_query_argument('next', '/'))


class RegisterHandler(BaseHandler):
    URL = ['/register', '/dzj_register.html']

    def get(self):
        """ 注册页面 """
        self.render('dzj_register.html', next=self.get_query_argument('next', '/'))


class UsersHandler(BaseHandler):
    URL = ['/user_manage', '/dzj_user_manage.html']

    @authenticated
    def get(self):
        """ 用户管理页面 """
        self.render('dzj_user_manage.html')
