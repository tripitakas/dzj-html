#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import logging
import random
import os.path
import smtplib
from email.header import Header
# 邮件文本
from email.mime.text import MIMEText
from datetime import datetime
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
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error_response(err)
        try:
            # 检查是否多次登录失败
            login_fail = {
                'type': 'login-fail',
                'create_time': {'$gt': hlp.get_date_time(diff_seconds=-1800)},
                'context': user.get('phone_or_email')
            }
            times = self.db.log.count_documents(login_fail)
            if times >= 20:
                return self.send_error_response(errors.unauthorized, message='登录失败，请半小时后重试，或者申请重置密码')

            login_fail['create_time']['$gt'] = hlp.get_date_time(diff_seconds=-60)
            times = self.db.log.count_documents(login_fail)
            if times >= 5:
                return self.send_error_response(errors.unauthorized, message='登录失败，请一分钟后重试')

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
                return self.send_error_response(errors.no_user)
            return
        if user['password'] != hlp.gen_id(password):
            if report_error:
                self.add_op_log('login-fail', context=phone_or_email)
                return self.send_error_response(errors.incorrect_password)
            return

        # 清除登录失败记录
        ResetUserPasswordApi.remove_login_fails(self, phone_or_email)

        user['roles'] = user.get('roles', '')
        user['login_md5'] = hlp.gen_id(user['roles'])
        self.current_user = user
        self.set_secure_cookie('user', json_util.dumps(user))

        self.add_op_log('login-ok', context=phone_or_email + ': ' + user['name'])
        logging.info('login id=%s, name=%s, phone_or_email=%s, roles=%s' %
                     (user['_id'], user['name'], phone_or_email, user['roles']))

        self.send_data_response(user)
        return user


class LogoutApi(BaseHandler):
    URL = '/api/user/logout'

    def get(self):
        """ 注销 """
        if self.current_user:
            self.clear_cookie('user')
            self.current_user = None
            self.add_op_log('logout')
            self.send_data_response()


class RegisterApi(BaseHandler):
    URL = '/api/user/register'

    def post(self):
        """ 注册 """
        user = self.get_request_data()
        rules = [
            (v.not_empty, 'name', 'password', 'email_code'),
            (v.not_both_empty, 'email', 'phone'),
            (v.is_name, 'name'),
            (v.is_email, 'email'),
            (v.is_phone, 'phone'),
            (v.is_password, 'password'),
            (v.not_existed, self.db.user, 'phone', 'email'),
            (v.code_verify_timeout, self.db.verify, 'email', 'email_code')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error_response(err)

        try:
            user['roles'] = '用户管理员' if not self.db.user.find_one() else ''  # 如果是第一个用户，则设置为用户管理员
            user['img'] = 'imgs/ava%s.png' % (1 if user.get('gender') == '男' else 2 if user.get('gender') == '女' else 3)

            r = self.db.user.insert_one(dict(
                name=user['name'], email=user.get('email'), phone=user.get('phone'),
                gender=user.get('gender'), roles=user['roles'], img=user['img'],
                password=hlp.gen_id(user['password']),
                create_time=hlp.get_date_time()
            ))
            user['_id'] = r.inserted_id
            self.add_op_log('register', context='%s: %s: %s' % (user.get('email'), user.get('phone'), user['name']))
        except DbError as e:
            return self.send_db_error(e)

        user['login_md5'] = hlp.gen_id(user['roles'])
        self.current_user = user
        self.set_secure_cookie('user', json_util.dumps(user))
        logging.info('register id=%s, name=%s, email=%s' % (user['_id'], user['name'], user.get('email')))
        self.send_data_response(user)


class ChangeUserProfileApi(BaseHandler):
    URL = r'/api/user/profile'

    def post(self):
        """ 修改用户基本信息: 姓名，手机，邮箱，性别"""
        user = self.get_request_data()
        rules = [
            (v.not_empty, 'name', '_id', 'email_code'),
            (v.not_both_empty, 'email', 'phone'),
            (v.is_name, 'name'),
            (v.is_email, 'email'),
            (v.is_phone, 'phone'),
            (v.not_existed, self.db.user, user['_id'], 'phone', 'email')
        ]
        err = v.validate(user, rules)
        if err:
            return self.send_error_response(err)

        try:
            old_user = self.db.user.find_one(dict(_id=user['_id']))
            if not old_user:
                return self.send_error_response(errors.no_user, id=user['_id'])

            sets = {f: user[f] for f in ['name', 'phone', 'email', 'gender']
                    if f in user and user[f] != old_user.get(f)}
            if not sets:
                return self.send_error_response(errors.no_change)

            r = self.db.user.update_one(dict(_id=user['_id']), {'$set': sets})
            if r.modified_count:
                self.add_op_log('change_user_profile', context='%s: %s' % (user['_id'], ','.join(sets.keys())))

            self.send_data_response(dict(info=sets))

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
            return self.send_error_response(err)

        try:
            user['roles'] = user.get('roles') or ''
            r = self.db.user.update_one(dict(_id=user['_id']), {'$set': dict(roles=user['roles'])})
            if not r.matched_count:
                return self.send_error_response(errors.no_user)
            self.add_op_log('change_role', context='%s: %s' % (user.get('_id'), user.get('roles')))
        except DbError as e:
            return self.send_db_error(e)
        self.send_data_response({'roles': user['roles']})


class ResetUserPasswordApi(BaseHandler):
    URL = r'/api/user/reset_pwd'

    def post(self):
        """ 重置用户密码 """

        user = self.get_request_data()
        rules = [(v.not_empty, '_id')]
        err = v.validate(user, rules)
        if err:
            return self.send_error_response(err)

        pwd = '%s%d' % (chr(random.randint(97, 122)), random.randint(10000, 99999))
        try:
            oid = objectid.ObjectId(user['_id'])
            r = self.db.user.update_one(dict(_id=oid), {'$set': dict(password=hlp.gen_id(pwd))})
            if not r.matched_count:
                return self.send_error_response(errors.no_user)

            user = self.db.user.find_one(dict(_id=oid))
            self.remove_login_fails(self, user['_id'])
            self.add_op_log('reset_password', context=': '.join(user))
        except DbError as e:
            return self.send_db_error(e)
        self.send_data_response({'password': pwd})

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
            return self.send_error_response(err)

        try:
            if user['_id'] == self.current_user['_id']:  # 判断删除的用户是否为自己
                return self.send_error_response(errors.cannot_delete_self)
            r = self.db.user.delete_one(dict(_id=user['_id']))
            if r.deleted_count < 1:
                return self.send_error_response(errors.no_user)
            self.add_op_log('delete_user', context=': '.join(user))
        except DbError as e:
            return self.send_db_error(e)
        self.send_data_response()


class ChangeMyPasswordApi(BaseHandler):
    URL = '/api/user/my/pwd'

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
            return self.send_error_response(err)

        try:
            u = self.db.user.find_one(dict(_id=self.current_user['_id']))
            if u.get('password') != hlp.gen_id(user['old_password']):
                return self.send_error_response(errors.incorrect_old_password)
            self.db.user.update_one(
                dict(_id=self.current_user['_id']),
                {'$set': dict(password=hlp.gen_id(user['password']))}
            )
            self.add_op_log('change_password')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change password %s' % self.current_user['name'])
        self.send_data_response()


class ChangeMyProfileApi(BaseHandler):
    URL = '/api/user/my/profile'

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
            return self.send_error_response(err)

        try:
            self.current_user['name'] = user.get('name') or self.current_user['name']
            self.current_user['gender'] = user.get('gender') or self.current_user.get('gender')
            self.current_user['email'] = user.get('email') or self.current_user['email']
            self.current_user['phone'] = user.get('phone') or self.current_user.get('phone')

            r = self.db.user.update_one(dict(_id=self.current_user['_id']), {
                '$set': dict(
                    name=self.current_user['name'],
                    gender=self.current_user.get('gender'),
                    email=self.current_user.get('email'),
                    phone=self.current_user.get('phone')
                )
            })
            if not r.modified_count:
                return self.send_error_response(errors.no_change)

            self.set_secure_cookie('user', json_util.dumps(self.current_user))
            self.add_op_log('change_profile')
        except DbError as e:
            return self.send_db_error(e)

        logging.info('change profile %s' % (user.get('name')))
        self.send_data_response()


class UploadUserImageHandler(BaseHandler):
    URL = '/api/user/upload_img'

    def post(self):

        """上传用户头像"""
        upload_img = self.request.files.get('img')
        img_name = str(self.current_user['_id']) + os.path.splitext(upload_img[0]['filename'])[-1]
        img = 'upload/avatar/' + img_name
        with open('static/' + img, 'wb') as f:
            f.write(upload_img[0]['body'])

        try:
            self.db.user.update_one(dict(_id=self.current_user['_id']), {'$set': dict(img=img)})
        except DbError as e:
            return self.send_db_error(e)

        self.current_user['img'] = img
        self.set_secure_cookie('user', json_util.dumps(self.current_user))
        self.send_data_response()


class SendUserEmailCodeHandler(BaseHandler):
    URL = '/api/user/send_email_code'

    def post(self):
        email = self.get_argument('email', None)
        if email:
            code = hlp.random_code()  # 获取随机验证码
            self.send_email(email, code)  # 发送验证码到邮箱
            email_exist = self.db.verify.find_one(dict(type='email', data=email))
            try:
                if not email_exist:
                    self.db.verify.insert_one(dict(type='email', data=email, code=code, stime=datetime.now()))
                else:
                    self.db.verify.update_one(dict(type='email', data=email), {'$set': dict(code=code, stime=datetime.now())})
            except DbError as e:
                return self.send_db_error(e)

        self.send_data_response()

    def send_email(self, receiver, content, subject="如是藏经邮箱验证"):  # email_list邮件列表，content邮件内容，subject：发送标题
        msg = MIMEText('<html><h1>验证码：'+content+'</h1></html>', 'html', 'utf-8')
        sender = '240144200@qq.com'  # 备用'tripitakas@163.com'
        pwd = 'oxlaqjdxlvzlcagf' # 备用'rstripitaka2019'  使用的是授权码
        msg['from'] = sender
        msg['to'] = receiver
        msg['Subject'] = Header(subject, 'utf-8')

        mail_host = "smtp.qq.com"  # 备用"smtp.163.com"
        mail_port = 25
        server = smtplib.SMTP(mail_host, mail_port)
        #邮箱引擎
        server.login(sender, pwd)  # 邮箱名，密码
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
