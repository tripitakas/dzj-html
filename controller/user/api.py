#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import logging
import random

from tornado.options import options

from bson import objectid, json_util
from controller import errors
from controller.base import BaseHandler, DbError
import controller.helper as hlp
import controller.validate as v


class LoginApi(BaseHandler):
    URL = '/api/user/login'

    def post(self):
        """ 登录 """
        user = self.get_request_data()
        rules = [
            (v.not_empty, 'phone_or_email', 'password'),
            (v.is_phone_or_email, 'phone_or_email'),
            (v.is_password, 'password')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            # 检查是否多次登录失败
            login_fail = {
                'type': 'login-fail',
                'create_time': {'$gt': hlp.get_date_time(diff_seconds=-1800)},
                'context': user.get('phone_or_email')
            }
            times = self.db.log.count_documents(login_fail)
            if times >= 20:
                return self.send_error(errors.unauthorized, reason='请半小时后重试，或者申请重置密码')

            login_fail['create_time']['$gt'] = hlp.get_date_time(diff_seconds=-60)
            times = self.db.log.count_documents(login_fail)
            if times >= 5:
                return self.send_error(errors.unauthorized, reason='请一分钟后重试')

            # 尝试登录，成功后清除登录失败记录，设置为当前用户
            self.login(self, user.get('phone_or_email'), user.get('password'))
        except DbError as e:
            return self.send_db_error(e)

    @staticmethod
    def login(self, phone_or_email, password, report_error=True):
        user = self.db.user.find_one({
            '$or': [
                {'email': phone_or_email},
                {'phone': phone_or_email}
            ]
        })
        if not user:
            if report_error:
                self.add_op_log('login-no-user', context=phone_or_email)
                return self.send_error(errors.no_user, reason=phone_or_email)
            return
        if user['password'] != hlp.gen_id(password):
            if report_error:
                self.add_op_log('login-fail', context=phone_or_email)
                return self.send_error(errors.incorrect_password)
            return

        # 清除登录失败记录
        ResetUserPasswordApi.remove_login_fails(self, phone_or_email)

        user['roles'] = user.get('roles', '')
        user['login_md5'] = hlp.gen_id(user['roles'])
        self.current_user = user
        self.set_secure_cookie('user', json_util.dumps(user))

        self.add_op_log('login-ok', context=phone_or_email + ': ' + user['name'])
        logging.info('login id=%s, name=%s, phone_or_email=%s, roles=%s' %
                     (user['id'], user['name'], phone_or_email, user['roles']))

        self.send_response(user)
        return user


class LogoutApi(BaseHandler):
    URL = '/api/user/logout'

    def get(self):
        """ 注销 """
        if self.current_user:
            self.clear_cookie('user')
            self.current_user = None
            self.add_op_log('logout')
            self.send_response()


class RegisterApi(BaseHandler):
    URL = '/api/user/register'

    def post(self):
        """ 注册 """
        user = self.get_request_data()

        # 单元测试时，如果用户已存在，则自动登录
        if options.testing and LoginApi.login(self, user.get('email'), user.get('password'), report_error=False):
            return

        rules = [
            (v.not_empty, 'name', 'password'),
            (v.not_both_empty, 'email', 'phone'),
            (v.is_name, 'name'),
            (v.is_email, 'email'),
            (v.is_phone, 'phone'),
            (v.is_password, 'password'),
            (v.not_existed, self.db.user, 'phone', 'email')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            user['roles'] = '用户管理员' if not self.db.user.find_one() else ''  # 如果是第一个用户，则设置为用户管理员
            r = self.db.user.insert_one(dict(name=user['name'], email=user.get('email'), phone=str(user.get('phone')),
                                             gender=user.get('gender'), roles=user['roles'],
                                             password=hlp.gen_id(user['password']),
                                             create_time=hlp.get_date_time()
                                             ))
            user['_id'] = r.inserted_id
            self.add_op_log('register', context=user.get('email') + ': ' + str(user.get('phone')) + ': ' + user['name'])
        except DbError as e:
            return self.send_db_error(e)

        user['login_md5'] = hlp.gen_id(user['roles'])
        self.current_user = user
        self.set_secure_cookie('user', json_util.dumps(user))
        logging.info('register id=%s, name=%s, email=%s' % (user['_id'], user['name'], user.get('email')))
        self.send_response(user)


class ChangeUserProfileApi(BaseHandler):
    URL = r'/api/user/profile'

    def post(self):
        """ 修改用户基本信息: 姓名，手机，邮箱，性别"""
        user = self.get_request_data()
        rules = [
            (v.not_empty, 'name', '_id'),
            (v.not_both_empty, 'email', 'phone'),
            (v.is_name, 'name'),
            (v.is_email, 'email'),
            (v.is_phone, 'phone'),
            (v.not_existed, self.db.user, user['_id'], 'phone', 'email')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            old_user = self.db.user.find_one(dict(_id=user['_id']))
            if not old_user:
                return self.send_error(errors.no_user, reason=str(user['_id']))

            sets = {f: user[f] for f in ['name', 'phone', 'email', 'gender'] if user.get(f) != old_user.get(f)}
            if not sets:
                return self.send_error(errors.no_change)

            r = self.db.user.update_one(dict(_id=user['_id']), {'$set': sets})
            if r.modified_count:
                self.add_op_log('change_user_profile', context=','.join([str(user['_id'])] + list(sets.keys())))

            self.send_response(dict(info=sets))

        except DbError as e:
            return self.send_db_error(e)


class ChangeUserRoleApi(BaseHandler):
    URL = r'/api/user/role'

    def post(self):
        """ 修改用户角色 """

        user = self.get_request_data()
        rules = [(v.not_empty, '_id')]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            user['roles'] = user.get('roles') or ''
            r = self.db.user.update_one(dict(_id=user['_id']), {'$set': dict(roles=user['roles'])})
            if not r.matched_count:
                return self.send_error(errors.no_user)
            self.add_op_log('change_role', context=(user.get('_id') + ': ' + user['roles']))
        except DbError as e:
            return self.send_db_error(e)
        self.send_response({'roles': user['roles']})


class ResetUserPasswordApi(BaseHandler):
    URL = r'/api/user/reset_pwd'

    def post(self):
        """ 重置用户密码 """

        user = self.get_request_data()
        rules = [(v.not_empty, '_id')]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        pwd = '%s%d' % (chr(random.randint(97, 122)), random.randint(10000, 99999))
        try:
            oid = objectid.ObjectId(user['_id'])
            r = self.db.user.update_one(dict(_id=oid), {'$set': dict(password=hlp.gen_id(pwd))})
            if not r.matched_count:
                return self.send_error(errors.no_user)

            user = self.db.user.find_one(dict(_id=oid))
            self.remove_login_fails(self, user['_id'])
            self.add_op_log('reset_password', context=': '.join(user))
        except DbError as e:
            return self.send_db_error(e)
        self.send_response({'password': pwd})

    @staticmethod
    def remove_login_fails(self, context):
        self.db.log.delete_many({
            'type': 'login-fail',
            'create_time': {'$gt': hlp.get_date_time(diff_seconds=-3600)},
            'context': context
        })

class DeleteUserApi(BaseHandler):
    URL = r'/api/user/delete'

    def post(self):
        """ 删除用户 """

        user = self.get_request_data()
        rules = [(v.not_empty, '_id')]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            r = self.db.user.delete_one(dict(_id=user['_id']))
            if not r.matched_count:
                return self.send_error(errors.no_user)

            self.add_op_log('delete_user', context=': '.join(user))
        except DbError as e:
            return self.send_db_error(e)
        self.send_response()


class ChangeMyPasswordApi(BaseHandler):
    URL = '/api/my/pwd'

    def post(self):
        """ 修改我的密码 """
        user = self.get_request_data()
        rules = [
            (v.not_empty, 'password', 'old_password'),
            (v.not_equal, 'password', 'old_password'),
            (v.is_password, 'password')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            u = self.db.user.find_one(dict(_id=self.current_user['_id']))
            if u.get('password') != hlp.gen_id(user['old_password']):
                return self.send_error(errors.incorrect_old_password)
            self.db.user.update_one(
                dict(_id=self.current_user['_id']),
                {'$set': dict(password=hlp.gen_id(user['password']))}
            )
            self.add_op_log('change_password')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change password %s' % self.current_user['name'])
        self.send_response()


class ChangeMyProfileApi(BaseHandler):
    URL = '/api/my/profile'

    def post(self):
        """ 修改我的个人信息，包括姓名、性别等 """
        user = self.get_request_data()
        rules = [
            (v.not_empty, 'name'),
            (v.not_both_empty, 'email', 'phone'),
            (v.is_name, 'name'),
            (v.is_email, 'email'),
            (v.is_phone, 'phone'),
            (v.not_existed, self.db.user, self.current_user['_id'], 'phone', 'email')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error(err)

        try:
            self.current_user['name'] = user.get('name') or self.current_user['name']
            self.current_user['gender'] = user.get('gender') or self.current_user.get('gender')
            self.current_user['email'] = user.get('email') or self.current_user['email']
            self.current_user['phone'] = user.get('phone') or self.current_user.get('phone')

            self.db.user.update_one(dict(_id=self.current_user['_id']), {
                '$set': dict(
                    name=self.current_user['name'],
                    gender=self.current_user.get('gender'),
                    email=self.current_user.get('email'),
                    phone=self.current_user.get('phone')
                )
            })

            self.set_secure_cookie('user', json_util.dumps(self.current_user))
            self.add_op_log('change_profile')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change profile %s' % (user.get('name')))
        self.send_response()
