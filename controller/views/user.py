#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""

from tornado.web import authenticated
from controller.base import BaseHandler, execute, fetch_authority, DbError
from pymysql.cursors import DictCursor
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
        sql = 'SELECT {0} FROM t_user'.format(','.join(fields))
        try:
            with self.connection as conn:
                self.update_login(conn)
                if u.ACCESS_MANAGER not in self.authority:
                    sql += ' and user_id="{0}"'.format(self.current_user.id)

                with conn.cursor(DictCursor) as cursor:
                    execute(cursor, sql)
                    users = [self.fetch2obj(r, u.User) for r in cursor.fetchall()]
                    users.sort(key=lambda a: a.name)
                    users = self.convert_for_send(users)
                    self.add_op_log(cursor, 'get_users', context='取到 %d 个用户' % len(users))

        except DbError as e:
            return self.send_db_error(e)

        self.render('dzj_user_manage.html', users=users)


class UserRolesHandler(BaseHandler):
    URL = '/dzj_user_role.html'

    @authenticated
    def get(self):
        """ 角色管理页面 """
        fields = ['a.id', 'a.name', 'email'] + list(u.authority_map.keys())
        sql = 'SELECT {0} FROM t_user a,t_authority b WHERE a.id=b.user_id'.format(','.join(fields))
        try:
            with self.connection as conn:
                self.update_login(conn)
                if u.ACCESS_MANAGER not in self.authority:
                    sql += ' and user_id="{0}"'.format(self.current_user.id)

                with conn.cursor(DictCursor) as cursor:
                    execute(cursor, sql)
                    users = [self.fetch2obj(r, u.User, fetch_authority) for r in cursor.fetchall()]
                    users.sort(key=lambda a: a.name)
                    users = self.convert_for_send(users)
                    self.add_op_log(cursor, 'get_users', context='取到 %d 个用户' % len(users))

        except DbError as e:
            return self.send_db_error(e)

        self.render('dzj_user_role.html', users=users)
