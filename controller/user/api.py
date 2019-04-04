#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import logging
import random
import re

from tornado.escape import json_encode, json_decode
from tornado.util import unicode_type

from controller import errors
from controller.base import BaseHandler, DbError
from controller.model import User
from controller.role import role_maps
import controller.helper as hlp

re_email = re.compile(r'^[a-z0-9][a-z0-9_.-]+@[a-z0-9_-]+(\.[a-z]+){1,2}$')
re_name = re.compile(br'^[\u4E00-\u9FA5]{2,5}$|^[A-Za-z][A-Za-z -]{2,19}$'.decode('raw_unicode_escape'))
re_password = re.compile(r'^[A-Za-z0-9,.;:!@#$%^&*-_]{6,18}$')
base_fields = ['id', 'name', 'email', 'phone', 'gender', 'roles', 'create_time']


def trim_user(r):
    r.password = None
    return r


class LoginApi(BaseHandler):
    URL = '/api/user/login'

    def post(self):
        """ 登录 """
        user = self.get_body_obj(User)
        email = user.email
        password = user.password

        if not email:
            return self.send_error(errors.need_email)
        if not password:
            return self.send_error(errors.need_password)
        email = email.lower()
        if not re_email.match(email):
            return self.send_error(errors.invalid_email)

        fields = base_fields + ['password']
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
            user = self.db.user.find_one(dict(email=email))
            user = self.fetch2obj(user, User, fields=fields)
            if not user:
                self.add_op_log('login-no', context=email)
                return self.send_error(errors.no_user, reason=email)
            if user.password != hlp.gen_id(password):
                self.add_op_log('login-fail', context=email)
                return self.send_error(errors.invalid_password)
            self.current_user = user
            self.add_op_log('login-ok', context=email + ': ' + user.name)
            ResetUserPasswordApi.remove_login_fails(self, email)
            user.login_md5 = hlp.gen_id(user.roles)
        except DbError as e:
            return self.send_db_error(e)

        user.__dict__.pop('old_password', 0)
        user.__dict__.pop('password', 0)
        user.__dict__.pop('last_time', 0)
        user.roles = user.roles or ''
        self.set_secure_cookie('user', json_encode(self.convert2dict(user)))
        logging.info('login id=%s, name=%s, email=%s, roles=%s' % (user.id, user.name, user.email, user.roles))

        self.send_response(user, trim=trim_user)


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

        user.id = hlp.gen_id(user.email, 'user')
        user.create_time = hlp.get_date_time()

        return True

    def post(self):
        """ 注册 """
        user = self.get_body_obj(User)
        if self.check_info(user):
            try:
                if self.db.user.find_one(dict(email=user.email)):
                    return self.send_error(errors.user_exists, reason=user.email)

                # 如果是第一个用户则设置为用户管理员
                first_user = not self.db.user.find_one({})
                user.roles = '用户管理员' if first_user else ''

                # 创建用户，分配权限，设置为当前用户
                self.db.user.insert_one(dict(
                    id=user.id, name=user.name, email=user.email,
                    password=hlp.gen_id(user.password),
                    roles=user.roles, create_time=user.create_time))

                self.add_op_log('register', context=user.email + ': ' + user.name)
            except DbError as e:
                return self.send_db_error(e)

            user.login_md5 = hlp.gen_id(user.roles)
            user.__dict__.pop('old_password', 0)
            user.__dict__.pop('password', 0)
            user.__dict__.pop('last_time', 0)
            self.current_user = user
            self.set_secure_cookie('user', json_encode(self.convert2dict(user)))
            logging.info('register id=%s, name=%s, email=%s' % (user.id, user.name, user.email))

            self.send_response(user, trim=trim_user)


class ChangeUserProfileApi(BaseHandler):
    URL = r'/api/user/profile'

    def check(self):
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)

        info = self.get_body_obj(User)
        if not info or not info.email:
            return self.send_error(errors.incomplete)
        if info.name and not re_name.match(unicode_type(info.name)):
            return self.send_error(errors.invalid_name)

        return info

    def post(self):
        """ 修改用户基本信息 """
        info = self.check()
        if not info:
            return

        try:
            old_user = self.fetch2obj(self.db.user.find_one(dict(email=info.email)), User)
            if not old_user:
                return self.send_error(errors.no_user, reason=info.email)
            info.id = old_user.id

            c1 = self.change_info(info, old_user)
            if c1 is not None:
                if not c1:
                    return self.send_error(errors.no_change)
                self.send_response(dict(info=c1))

        except DbError as e:
            return self.send_db_error(e)

    def change_info(self, info, old_user):
        sets = {f: info.__dict__[f] for f in ['name', 'phone', 'gender']
                if info.__dict__.get(f) and info.__dict__[f] != old_user.__dict__[f]}
        if sets:
            if self.current_user.id != info.id and '用户管理员' not in self.current_user.roles:
                return self.send_error(errors.unauthorized, reason='用户管理员')

            if info.name and not re_name.match(unicode_type(info.name)):
                return self.send_error(errors.invalid_name, reason=info.name) or -1

            r = self.db.user.update_one(dict(email=info.email), {'$set': sets})
            if r.modified_count:
                self.add_op_log('change_user', context=','.join([info.email] + list(sets.keys())))
                return list(sets.keys())
        return []


class ChangeUserRoleApi(BaseHandler):
    URL = r'/api/user/role'

    def check(self):
        self.current_user = self.get_current_user()
        if not self.current_user:
            return self.send_error(errors.need_login)

        info = self.get_body_obj(User)
        if not info or not info.email:
            return self.send_error(errors.incomplete)

        return info

    def post(self):
        """ 修改用户角色 """
        info = self.check()
        if not info:
            return

        try:
            old_user = self.fetch2obj(self.db.user.find_one(dict(email=info.email)), User)
            if not old_user:
                return self.send_error(errors.no_user, reason=info.email)
            old_roles = old_user.roles
            info.id = old_user.id

            c2 = info.roles is not None and self.change_roles(info, old_roles)
            if c2 is not None:
                if c2 == 1:
                    return self.send_error(errors.no_change)
                self.send_response(dict(roles=c2))

        except DbError as e:
            return self.send_db_error(e)

    def change_roles(self, info, old_auth):
        c2 = 1
        sets = {role: int(role_desc in info.roles) for role, role_desc in role_maps.items()
                if role not in ['user'] and (role_desc in info.roles) != (role_desc in old_auth)}
        if sets:
            sets = [role for role, v in sets.items() if v]
            if '用户管理员' not in self.current_user.roles:
                return self.send_error(errors.unauthorized, reason='需要由管理员修改权限')
            if '用户管理员' not in info.roles and '用户管理员' in old_auth \
                    and info.id == self.current_user.id:
                return self.send_error(errors.unauthorized, reason='不能取消自己的管理员权限')

            r = self.db.user.update_one(dict(email=info.email), {'$set': dict(roles=','.join(sets))})
            if r.modified_count:
                c2 = 2
                self.add_op_log('change_user', context=','.join([info.email] + sets))
        return c2


class ResetUserPasswordApi(BaseHandler):
    URL = r'/api/user/reset_pwd'

    def post(self):
        """ 重置用户密码 """

        uid = json_decode(self.get_body_argument('data'))['user_id']
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
        info = self.get_body_obj(User)
        if not info or not info.email or not info.name:
            return self.send_error(errors.incomplete)
        if info.email == self.current_user.email:
            return self.send_error(errors.unauthorized, reason='不能删除自己')

        try:
            r = self.db.user.delete_one(dict(name=info.name, email=info.email))
            if not r.deleted_count:
                return self.send_error(errors.no_user)
            self.add_op_log('remove_user', context=info.email + ': ' + info.name)
        except DbError as e:
            return self.send_db_error(e)

        logging.info('remove user %s %s' % (info.name, info.email))
        self.send_response()


class GetUsersApi(BaseHandler):
    URL = '/api/user/list'

    def get(self):
        """ 得到全部用户 """
        try:
            users = self.db.user.find({})  # Todo 这里要按分页来取
            users = [self.fetch2obj(r, User, fields=base_fields) for r in users]
            users.sort(key=lambda a: a.name)
            users = self.convert_for_send(users, trim=trim_user)
            self.add_op_log('get_users', context='取到 %d 个用户' % len(users))

        except DbError as e:
            return self.send_db_error(e)

        response = dict(items=users, roles=self.current_user.roles, time=hlp.get_date_time())
        self.send_response(response)


class ChangeMyPasswordApi(BaseHandler):
    URL = '/api/my/pwd'

    def post(self):
        """ 修改我的密码 """
        info = self.get_body_obj(User)
        if not info:
            return self.send_error(errors.incomplete)
        if not info.password:
            return self.send_error(errors.need_password)
        if not info.old_password:
            return self.send_error(errors.incomplete, reason="缺原密码")
        if not re_password.match(info.password) or re.match(r'^(\d+|[A-Za-z]+)$', info.password):
            return self.send_error(errors.invalid_psw_format)
        if info.password == info.old_password:
            return self.send_response()

        try:
            r = self.db.user.find_one(dict(id=self.current_user.id))
            if not r:
                return self.send_error(errors.no_user)
            if r.get('password') != hlp.gen_id(info.old_password):
                return self.send_error(errors.invalid_password)
            self.db.user.update_one(
                dict(id=self.current_user.id, password=hlp.gen_id(info.old_password)),
                {'$set': dict(password=hlp.gen_id(info.password))}
            )
            self.add_op_log('change_pwd')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change password %s %s' % (info.id, info.name))
        self.send_response()


class ChangeMyProfileApi(BaseHandler):
    URL = '/api/my/profile'

    def post(self):
        """ 修改我的个人信息，包括姓名、性别等 """
        info = self.get_body_obj(User)
        try:
            self.db.user.update_one(
                dict(id=self.current_user.id),
                {'$set': dict(name=info.name, gender=info.gender)}
            )
            self.current_user.name = info.name
            self.current_user.gender = info.gender
            self.set_secure_cookie('user', json_encode(self.convert2dict(self.current_user)))
            self.add_op_log('change_profile')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change profile %s %s' % (info.id, info.name))
        self.send_response()
