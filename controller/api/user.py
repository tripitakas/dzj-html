#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Zhang Yungui
@time: 2018/10/23
"""

import logging
import random
import re

from pymysql.constants import ER
from pymysql.cursors import DictCursor
from tornado.escape import json_encode
from tornado.util import unicode_type

import model.user as u
from controller import errors
from controller.base import BaseHandler, DbError, execute, fetch_authority

re_email = re.compile(r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$')
re_name = re.compile(br'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'.decode('raw_unicode_escape'))
re_password = re.compile(r'^[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$')
base_fields = ['id', 'name', 'email', 'phone', 'create_time']


def trim_user(r):
    r.password = None
    return r


class LoginApi(BaseHandler):
    URL = '/api/user/login'

    def post(self):
        """ 登录 """
        user = self.get_body_obj(u.User)
        email = user.email
        password = user.password

        if not email:
            return self.send_error(errors.need_email)
        if not password:
            return self.send_error(errors.need_password)
        email = email.lower()
        if not re_email.match(email):
            return self.send_error(errors.invalid_email)

        fields = base_fields + ['password'] + list(u.authority_map.keys())
        sql = 'SELECT {0} FROM t_user a,t_authority b WHERE email=%s and a.id=b.user_id'.format(','.join(fields))
        sql_fail = 'SELECT count(*) FROM t_op_log WHERE type="login-fail" and ' \
                   'TIMESTAMPDIFF(SECOND,create_time,NOW()) < 1800 and context LIKE "% {0}"'.format(email)
        try:
            with self.connection as conn:
                # 检查是否多次登录失败
                with conn.cursor() as cursor:
                    execute(cursor, sql_fail)
                    times = cursor.fetchone()[0]
                    if times >= 20:
                        return self.send_error(errors.unauthorized, reason='请半小时后重试，或者申请重置密码')
                    r = times >= 5 and execute(cursor, sql_fail.replace('< 1800', '< 60'))
                    times = r and cursor.fetchone()[0] or 0
                    if times >= 5:
                        return self.send_error(errors.unauthorized, reason='请一分钟后重试')

                # 尝试登录，成功后清除登录失败记录，设置为当前用户
                with conn.cursor(DictCursor) as cursor:
                    execute(cursor, sql, (email,))
                    user = self.fetch2obj(cursor.fetchone(), u.User, fetch_authority)
                    if not user:
                        self.add_op_log(cursor, 'login-no', context='账号不存在: ' + email)
                        return self.send_error(errors.no_user, reason=email)
                    if user.password != errors.gen_id(password):
                        self.add_op_log(cursor, 'login-fail', context='密码错误: ' + email)
                        return self.send_error(errors.invalid_password)
                    self.current_user = user
                    self.add_op_log(cursor, 'login-ok', context=email + ': ' + user.name)
                    ResetPasswordApi.remove_login_fails(cursor, email)
                    user.login_md5 = errors.gen_id(user.authority)
        except DbError as e:
            return self.send_db_error(e)

        user.__dict__.pop('old_password', 0)
        user.__dict__.pop('password', 0)
        user.__dict__.pop('last_time', 0)
        self.authority = user.authority
        self.set_secure_cookie('user', json_encode(self.convert2dict(user)))
        logging.info('login id=%s, name=%s, email=%s, auth=%s' % (user.id, user.name, user.email, user.authority))

        self.send_response(user, trim=trim_user)


class RegisterApi(BaseHandler):
    URL = '/api/user/register'

    def check_info(self, user):
        if not user:
            return self.send_error(errors.incomplete)
        if not user.email:
            return self.send_error(errors.need_email)
        if not user.name:
            return self.send_error(errors.incomplete, reason='姓名')
        if not user.password:
            return self.send_error(errors.need_password)

        user.email = user.email.lower()
        if not re_email.match(user.email):
            return self.send_error(errors.invalid_email)
        if not re_password.match(user.password) or re.match(r'^(\d+|[A-Z]+|[a-z]+)$', user.password):
            return self.send_error(errors.invalid_psw_format)

        if not re_name.match(unicode_type(user.name)):
            return self.send_error(errors.invalid_name, reason=user.name)

        user.id = errors.gen_id(user.email, 'user')
        user.create_time = errors.get_date_time()
        self.authority = user.authority = ''

        return True

    def post(self):
        """ 注册 """
        user = self.get_body_obj(u.User)
        if self.check_info(user):
            try:
                with self.connection as conn:
                    # 如果是第一个用户则设置为管理员
                    with conn.cursor() as cursor:
                        execute(cursor, 'SELECT count(*) FROM t_user')
                        mgr = cursor.fetchone()[0] == 0

                    # 创建用户，分配权限，设置为当前用户
                    sql = self.insert_sql('t_user', dict(
                        id=user.id, name=user.name, email=user.email,
                        password=errors.gen_id(user.password), create_time=user.create_time))
                    with conn.cursor() as cursor:
                        execute(cursor, *sql)
                        user.authority = u.ACCESS_MANAGER if mgr else ''
                        execute(cursor, *self.insert_sql('t_authority', dict(user_id=user.id, manager=int(mgr))))
                        self.current_user = user
                        self.add_op_log(cursor, 'register', context=user.email + ': ' + user.name)
            except DbError as e:
                if e.args[0] == ER.DUP_ENTRY:
                    return self.send_error(errors.user_exists, reason=user.email)
                return self.send_db_error(e)

            user.login_md5 = errors.gen_id(user.authority)
            user.__dict__.pop('old_password', 0)
            user.__dict__.pop('password', 0)
            user.__dict__.pop('last_time', 0)
            self.authority = user.authority
            self.set_secure_cookie('user', json_encode(self.convert2dict(user)))
            logging.info('register id=%s, name=%s, email=%s' % (user.id, user.name, user.email))

            self.send_response(user, trim=trim_user)


class ChangeUserApi(BaseHandler):
    URL = '/api/user/change'

    def check(self):
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)

        info = self.get_body_obj(u.User)
        if not info or not info.email or not info.id:
            return self.send_error(errors.incomplete)
        if info.name and not re_name.match(unicode_type(info.name)):
            return self.send_error(errors.invalid_name)

        return info

    def post(self):
        """ 改变用户的姓名等属性 """
        info = self.check()
        if not info:
            return

        with self.connection as conn:
            if not self.update_login(conn):
                return self.send_error(errors.auth_changed)
            if not self.authority:
                return self.send_error(errors.unauthorized)
            try:
                with conn.cursor(DictCursor) as cursor:
                    fields = base_fields + list(u.authority_map.keys())
                    sql = 'SELECT {0} FROM t_user a,t_authority b WHERE user_id=%s and a.id=b.user_id'.format(
                        ','.join(fields))
                    execute(cursor, sql, (info.id,))
                    old_user = self.fetch2obj(cursor.fetchone(), u.User, fetch_authority)
                    if not old_user:
                        return self.send_error(errors.no_user, reason=info.email)
                    old_auth = old_user.authority

                c1 = self.change_info(conn, info, old_user, old_auth)
                c2 = c1 != -1 and info.authority is not None and self.change_auth(conn, info, old_auth)
                if c2:
                    if not c1 and c2 == 1:
                        return self.send_error(errors.no_change)
                    self.send_response()

            except DbError as e:
                return self.send_db_error(e)

    def change_info(self, conn, info, old_user, old_auth):
        sets = ["{0}='{1}'".format(f, info.__dict__[f]) for f in ['name', 'phone']
                if info.__dict__.get(f) and info.__dict__[f] != old_user.__dict__[f]]
        if sets:
            if self.current_user.id != info.id and u.ACCESS_MANAGER not in self.authority:
                return self.send_error(errors.unauthorized)

            if info.name and not re_name.match(unicode_type(info.name)):
                return self.send_error(errors.invalid_name, reason=info.name) or -1

            with conn.cursor() as cursor:
                sql = 'UPDATE t_user SET {0} WHERE email=%s'.format(','.join(sets))
                c1 = execute(cursor, sql, (info.email,))
                if c1:
                    self.add_op_log(cursor, 'change_user', context=','.join([info.email] + sets))
            sets = str(sets)
            return (1 if 'name=' in sets else 0) + (2 if 'phone=' in sets else 0) if c1 else 0

    def change_auth(self, conn, info, old_auth):
        c2 = 1
        if old_auth != info.authority:
            if u.ACCESS_MANAGER not in self.authority:
                return self.send_error(errors.unauthorized)

            with conn.cursor() as cursor:
                sets = ['%s=%d' % (f, hz in info.authority) for f, hz in u.authority_map.items()
                        if (hz in info.authority) != (hz in old_auth)]
                sql = 'UPDATE t_authority SET {0} WHERE user_id=%s'.format(','.join(sets))
                c2 = execute(cursor, sql, (info.id,)) + 1
                if c2 > 1:
                    self.add_op_log(cursor, 'change_user', context=','.join([info.email] + sets))
        return c2


class LogoutApi(BaseHandler):
    URL = '/api/user/logout'

    def get(self):
        """ 注销 """
        if self.current_user:
            self.add_op_log(None, 'logout')
        self.clear_cookie('user')
        self.send_response()

    def post(self):
        """ 删除用户 """
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)

        info = self.get_body_obj(u.User)
        if not info or not info.email or not info.name:
            return self.send_error(errors.incomplete)
        if info.email == self.current_user.email:
            return self.send_error(errors.unauthorized, reason='不能删除自己')

        try:
            with self.connection as conn:
                self.update_login(conn)
                if u.ACCESS_MANAGER not in self.authority:
                    return self.send_error(errors.unauthorized, reason=u.ACCESS_MANAGER)

                with conn.cursor() as cursor:
                    r = execute(cursor, 'DELETE FROM t_user WHERE name=%s and email=%s', (info.name, info.email))
                    if not r:
                        return self.send_error(errors.no_user)
                    self.add_op_log(cursor, 'remove_user', context=info.email + ': ' + info.name)
        except DbError as e:
            return self.send_db_error(e)

        logging.info('remove user %s %s' % (info.name, info.email))
        self.send_response()


class GetUsersApi(BaseHandler):
    URL = '/api/user/list'

    def get(self):
        """ 得到全部用户 """
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)

        fields = base_fields + list(u.authority_map.keys())
        sql = '(select create_time from t_op_log where user_id=a.id order by create_time desc limit 1) as last_time'
        sql = 'SELECT {0},{1} FROM t_user a,t_authority b WHERE a.id=b.user_id'.format(
                    ','.join('a.' + f if f in 'id,name' else f for f in fields), sql)
        try:
            with self.connection as conn:
                error = None
                self.update_login(conn)
                if u.ACCESS_MANAGER not in self.authority:
                    error = '您还无权限做管理操作'
                if u.ACCESS_MANAGER not in self.authority:
                    sql += ' and user_id="{0}"'.format(self.current_user.id)

                with conn.cursor(DictCursor) as cursor:
                    execute(cursor, sql)
                    users = [self.fetch2obj(r, u.User, fetch_authority) for r in cursor.fetchall()]
                    users.sort(key=lambda a: a.name)
                    users = self.convert_for_send(users, trim=trim_user)
                    self.add_op_log(cursor, 'get_users', context='取到 %d 个用户' % len(users))

        except DbError as e:
            return self.send_db_error(e)

        response = dict(items=users, authority=self.authority, time=errors.get_date_time())
        if error:
            response['not_auth'] = error
        self.send_response(response)


class GetOptionsApi(BaseHandler):
    URL = r'/api/options/(\w+)'

    def get(self, kind):
        """ 得到配置项列表 """
        ret = self.application.config.get(kind)
        if not ret:
            return self.send_error(errors.invalid_parameter)
        self.send_response(ret)


class ResetPasswordApi(BaseHandler):
    URL = r'/api/pwd/reset/(\w+)'

    def post(self, rid):
        """ 重置一个用户的密码 """
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)

        pwd = '%s%d' % (chr(random.randint(97, 122)), random.randint(10000, 99999))
        try:
            with self.connection as conn:
                self.update_login(conn)
                if u.ACCESS_MANAGER not in self.authority:
                    return self.send_error(errors.unauthorized)

                with conn.cursor() as cursor:
                    r = execute(cursor, 'UPDATE t_user SET password=%s WHERE id=%s', (errors.gen_id(pwd), rid))
                    if not r:
                        return self.send_error(errors.no_user)

                    execute(cursor, 'SELECT email,name FROM t_user WHERE id=%s', (rid,))
                    user = cursor.fetchone()
                    self.remove_login_fails(cursor, user[0])
                    self.add_op_log(cursor, 'reset_pwd', context=': '.join(user))
        except DbError as e:
            return self.send_db_error(e)
        self.send_response({'password': pwd})

    @staticmethod
    def remove_login_fails(cursor, email):
        execute(cursor, 'DELETE FROM t_op_log WHERE type="login-fail" and '
                        'TIMESTAMPDIFF(SECOND,create_time,NOW()) < 3600 and '
                        'context LIKE "% {0}"'.format(email))


class ChangePasswordApi(BaseHandler):
    URL = '/api/pwd/change'

    def post(self):
        """ 修改当前用户的密码 """
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)
        info = self.get_body_obj(u.User)
        if not info:
            return self.send_error(errors.incomplete)
        if not info.password:
            return self.send_error(errors.need_password)
        if not info.old_password:
            return self.send_error(errors.incomplete, reason="缺原密码")
        if not re_password.match(info.password) or re.match(r'^(\d+|[A-Z]+|[a-z]+)$', info.password):
            return self.send_error(errors.invalid_psw_format)
        if info.password == info.old_password:
            return self.send_response()

        try:
            with self.connection as conn:
                self.update_login(conn)
                with conn.cursor() as cursor:
                    sql = 'UPDATE t_user SET password=%s WHERE id=%s and password=%s'
                    r = execute(cursor, sql, (errors.gen_id(info.password), self.current_user.id,
                                              errors.gen_id(info.old_password)))
                    if not r:
                        execute(cursor, 'SELECT name FROM t_user WHERE id=%s', (self.current_user.id,))
                        return self.send_error(errors.invalid_password if cursor.fetchone() else errors.no_user)
                    self.add_op_log(cursor, 'change_pwd')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change password %s %s' % (info.id, info.name))
        self.send_response()
