#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base import BaseHandler, fetch_authority, DbError
import model.user as u


class LoginHandler(BaseHandler):
    URL = ['/login', '/dzj_login.html']

    def get(self):
        """ 登录页面 """
        self.render('dzj_login.html', next=self.get_query_argument('next', '/'))


class RegisterHandler(BaseHandler):
    URL = '/dzj_register.html'

    def get(self):
        """ 注册页面 """
        self.render('dzj_register.html', next=self.get_query_argument('next', '/'))


class UsersHandler(BaseHandler):
    URL = '/dzj_user_manage.html'

    @authenticated
    def get(self):
        """ 用户管理页面 """
        fields = ['id', 'name', 'phone', 'email', 'gender', 'status', 'create_time']
        try:
            self.update_login()
            cond = {} if u.ACCESS_MANAGER in self.authority else dict(id=self.current_user.id)
            users = self.db.user.find(cond)
            users = [self.fetch2obj(r, u.User, fields=fields) for r in users]
            users.sort(key=lambda a: a.name)
            users = self.convert_for_send(users, trim=self.trim_user)
            self.add_op_log('get_users', context='取到 %d 个用户' % len(users))

        except DbError as e:
            return self.send_db_error(e)

        self.render('dzj_user_manage.html', users=users)

    @staticmethod
    def trim_user(r):
        r.image = 'imgs/' + {'': 'ava3.png', '女': 'ava.png', '男': 'ava2.png'}[r.gender or '']
        return r


class UserRolesHandler(BaseHandler):
    URL = '/dzj_user_role.html'

    @authenticated
    def get(self):
        """ 角色管理页面 """
        fields = ['a.id', 'name', 'phone', 'email'] + list(u.authority_map.keys())
        sql = 'SELECT {0} FROM t_user a,t_authority b WHERE a.id=b.user_id'.format(','.join(fields))
        try:
            self.update_login()
            cond = {} if u.ACCESS_MANAGER in self.authority else dict(id=self.current_user.id)
            users = self.db.user.find(cond)
            users = [self.fetch2obj(r, u.User, fetch_authority, fields=fields) for r in users]
            users.sort(key=lambda a: a.name)
            users = self.convert_for_send(users)
            self.add_op_log('get_users', context='取到 %d 个用户' % len(users))

        except DbError as e:
            return self.send_db_error(e)

        self.render('dzj_user_role.html', users=users, roles=['普通用户'] + u.ACCESS_ALL)
