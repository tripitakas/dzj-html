#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import logging
import random
import re

from tornado.escape import json_encode
from tornado.util import unicode_type

from controller import errors
from controller.base import BaseHandler, DbError
import controller.helper as hlp

re_email = re.compile(r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$')
re_name = re.compile(br'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'.decode('raw_unicode_escape'))
re_password = re.compile(r'^[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$')
base_fields = ['id', 'name', 'email', 'phone', 'gender', 'roles', 'create_time']


def trim_user(r):
    r.pop('password', 0)
    return r


class LoginApi(BaseHandler):
    URL = '/api/user/login'

    def post(self):
        """ 登录 """
        user = self.get_request_data()
        email, password = user.get('email'), user.get('password')

        if not email:
            return self.send_error(errors.need_phone_or_email)
        if not password:
            return self.send_error(errors.need_password)
        email = email.lower()
        if not re_email.match(email):
            return self.send_error(errors.invalid_email)

        try:
            # 检查是否多次登录失败
            login_fail = {
                'type': 'login-fail',
                'create_time': {'$gt': hlp.get_date_time(diff_seconds=-1800)},
                'context': email
            }
            times = self.db.log.count_documents(login_fail)

            if times >= 20:
                return self.send_error(errors.unauthorized, reason='请半小时后重试，或者申请重置密码')
            login_fail['create_time']['$gt'] = hlp.get_date_time(diff_seconds=-60)
            times = self.db.log.count_documents(login_fail)
            if times >= 5:
                return self.send_error(errors.unauthorized, reason='请一分钟后重试')

            # 尝试登录，成功后清除登录失败记录，设置为当前用户
            self.login(self, email, password)
        except DbError as e:
            return self.send_db_error(e)

    @staticmethod
    def login(self, email, password, report_error=True):
        user = self.db.user.find_one(dict(email=email))
        user = self.fetch2obj(user, fields=base_fields + ['password'])
        if not user:
            if report_error:
                self.add_op_log('login-no', context=email)
                return self.send_error(errors.no_user, reason=email)
            return
        if user['password'] != hlp.gen_id(password):
            if report_error:
                self.add_op_log('login-fail', context=email)
                return self.send_error(errors.incorrect_password)
            return

        self.current_user = user
        self.add_op_log('login-ok', context=email + ': ' + user['name'])
        ResetUserPasswordApi.remove_login_fails(self, email)
        user['login_md5'] = hlp.gen_id(user.get('roles'))
        user['roles'] = user.get('roles') or ''

        user.pop('old_password', 0)
        user.pop('password', 0)
        user.pop('last_time', 0)
        self.current_user = user
        self.set_secure_cookie('user', json_encode(user))
        logging.info('login id=%s, name=%s, email=%s, roles=%s' % (
            user['id'], user['name'], user['email'], user['roles']))

        self.send_response(trim_user(user))
        return user


class LogoutApi(BaseHandler):
    URL = '/api/user/logout'

    def get(self):
        """ 注销 """
        if self.current_user:
            self.add_op_log('logout')
            self.clear_cookie('user')
            self.send_response({'result': 'ok'})


class RegisterApi(BaseHandler):
    URL = '/api/user/register'

    def check_info(self, user):
        if not user:
            return self.send_error(errors.incomplete)
        if not user.get('name'):
            return self.send_error(errors.incomplete, reason='姓名')
        if not user.get('password'):
            return self.send_error(errors.need_password)
        if not user.get('phone') and not user.get('email'):
            return self.send_error(errors.need_phone_or_email)

        if user.get('email'):
            user['email'] = user['email'].lower()
            if not re_email.match(user['email']):
                return self.send_error(errors.invalid_email)

        if not re_password.match(user['password']) or re.match(r'^(\d+|[A-Z]+|[a-z]+)$', user['password']):
            return self.send_error(errors.invalid_psw_format)

        if not re_name.match(unicode_type(user['name'])):
            return self.send_error(errors.invalid_name, reason=user['name'])

        user['id'] = hlp.gen_id(str(user.get('phone')) + user.get('email'), 'user')
        user['create_time'] = hlp.get_date_time()

        return True

    def post(self):
        """ 注册 """
        user = self.get_request_data()
        if self.check_info(user):
            try:
                exist_user = self.db.user.find_one(dict(email=user['email']))
                if exist_user:
                    # 尝试自动登录，可用在自动测试上
                    return None if LoginApi.login(self, user['email'], user['password'], report_error=False) \
                        else self.send_error(errors.user_exists, reason=user['email'])

                # 如果是第一个用户则设置为用户管理员
                first_user = not self.db.user.find_one({})
                user['roles'] = '用户管理员' if first_user else ''

                # 创建用户，分配权限，设置为当前用户
                self.db.user.insert_one(dict(
                    id=user['id'], name=user['name'], email=user.get('email'), phone=user.get('phone'),
                    gender=user.get('gender'), password=hlp.gen_id(user['password']),
                    roles=user['roles'], create_time=user['create_time']))

                self.add_op_log('register', context=user['email'] + ': ' + user['name'])
            except DbError as e:
                return self.send_db_error(e)

            user['login_md5'] = hlp.gen_id(user['roles'])
            user.pop('old_password', 0)
            user.pop('password', 0)
            user.pop('last_time', 0)
            self.current_user = user
            self.set_secure_cookie('user', json_encode(user))
            logging.info('register id=%s, name=%s, email=%s' % (user['id'], user['name'], user['email']))

            self.send_response(trim_user(user))


class ChangeUserProfileApi(BaseHandler):
    URL = r'/api/user/profile'

    def post(self):
        """ 修改用户基本信息 """
        user = self.get_request_data()
        if user.get('name') and not re_name.match(unicode_type(user['name'])):
            return self.send_error(errors.invalid_name, reason=user['name']) or -1

        try:
            old_user = self.fetch2obj(self.db.user.find_one(dict(id=user['id'])))
            if not old_user:
                return self.send_error(errors.no_user, reason=user['id'])

            sets = {f: user[f] for f in ['name', 'phone', 'email', 'gender']
                    if user.get(f) and user.get(f) != old_user.get(f)}
            if not sets:
                return self.send_error(errors.no_change)

            r = self.db.user.update_one(dict(id=user['id']), {'$set': sets})
            if r.modified_count:
                self.add_op_log('change_user_profile', context=','.join([user['id']] + list(sets.keys())))

            self.send_response(dict(info=sets))

        except DbError as e:
            return self.send_db_error(e)


class ChangeUserRoleApi(BaseHandler):
    URL = r'/api/user/role'

    def post(self):
        """ 修改用户角色 """

        user = self.get_request_data()
        try:
            user['roles'] = user.get('roles') or ''
            r = self.db.user.update_one({'$or': [{'id': user.get('id')}, {'email': user.get('email')}]},
                                        {'$set': dict(roles=user['roles'])})
            if not r.matched_count:
                return self.send_error(errors.no_user)
            self.add_op_log('change_role',
                            context=(user.get('id') or user.get('email')) + ': ' + user['roles'])
        except DbError as e:
            return self.send_db_error(e)
        self.send_response({'roles': user['roles']})


class ResetUserPasswordApi(BaseHandler):
    URL = r'/api/user/reset_pwd'

    def post(self):
        """ 重置用户密码 """

        user = self.get_request_data()
        uid = user['id']
        pwd = '%s%d' % (chr(random.randint(97, 122)), random.randint(10000, 99999))
        try:
            r = self.db.user.update_one(dict(id=uid), {'$set': dict(password=hlp.gen_id(pwd))})
            if not r.matched_count:
                return self.send_error(errors.no_user)

            user = self.db.user.find_one(dict(id=uid))
            self.remove_login_fails(self, user['email'])
            self.add_op_log('reset_pwd', context=': '.join(user))
        except DbError as e:
            return self.send_db_error(e)
        self.send_response({'password': pwd})

    @staticmethod
    def remove_login_fails(self, email):
        self.db.log.delete_many({
            'type': 'login-fail',
            'create_time': {'$gt': hlp.get_date_time(diff_seconds=-3600)},
            'context': email
        })


class RemoveUserApi(BaseHandler):
    URL = '/api/user/remove'

    def post(self):
        """ 删除用户 """
        user = self.get_request_data()
        if not user or not user.get('email') or not user.get('name'):
            return self.send_error(errors.incomplete)
        if user['email'] == self.current_user['email']:
            return self.send_error(errors.unauthorized, reason='不能删除自己')

        try:
            r = self.db.user.delete_one(dict(name=user.get('name'), email=user['email']))
            if not r.deleted_count:
                return self.send_error(errors.no_user)
            self.add_op_log('remove_user', context=user['email'] + ': ' + user.get('name'))
        except DbError as e:
            return self.send_db_error(e)

        logging.info('remove user %s %s' % (user.get('name'), user['email']))
        self.send_response()


class ChangeMyPasswordApi(BaseHandler):
    URL = '/api/my/pwd'

    def post(self):
        """ 修改我的密码 """
        user = self.get_request_data()
        if not user:
            return self.send_error(errors.incomplete)
        if not user.get('password'):
            return self.send_error(errors.need_password)
        if not user.get('old_password'):
            return self.send_error(errors.incomplete, reason="缺原密码")
        if not re_password.match(user['password']) or re.match(r'^(\d+|[A-Za-z]+)$', user['password']):
            return self.send_error(errors.invalid_psw_format)
        if user['password'] == user['old_password']:
            return self.send_response()

        try:
            r = self.db.user.find_one(dict(id=self.current_user['id']))
            if not r:
                return self.send_error(errors.no_user)
            if r.get('password') != hlp.gen_id(user['old_password']):
                return self.send_error(errors.incorrect_password)
            self.db.user.update_one(
                dict(id=self.current_user['id'], password=hlp.gen_id(user['old_password'])),
                {'$set': dict(password=hlp.gen_id(user['password']))}
            )
            self.add_op_log('change_pwd')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change password %s %s' % (self.current_user['id'], self.current_user['name']))
        self.send_response()


class ChangeMyProfileApi(BaseHandler):
    URL = '/api/my/profile'

    def post(self):
        """ 修改我的个人信息，包括姓名、性别等 """
        user = self.get_request_data()
        try:
            self.db.user.update_one(
                dict(id=self.current_user['id']),
                {'$set': dict(name=user.get('name') or self.current_user['name'],
                              gender=user.get('gender') or self.current_user.get('gender'))}
            )
            self.current_user['name'] = user.get('name') or self.current_user['name']
            self.current_user['gender'] = user.get('gender') or self.current_user.get('gender')
            self.set_secure_cookie('user', json_encode(self.current_user))
            self.add_op_log('change_profile')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change profile %s %s' % (user['name'], user.get('name')))
        self.send_response()
