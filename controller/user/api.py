#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

import random
import logging
import smtplib
from os import path
from bson import json_util
from bson.objectid import ObjectId
from tornado.options import options
from tornado.web import urlencode
from datetime import datetime, timedelta

from email.header import Header
from email.mime.text import MIMEText
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from controller import helper
from controller import errors as e
from controller import validate as v
from controller.user.user import User
from controller.base import BaseHandler, DbError


class LoginApi(BaseHandler):
    URL = '/api/user/login'

    def post(self):
        """ 登录 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'phone_or_email', 'password')]
            v.validate(data, rules, self)

            # 检查是否多次登录失败
            gap = datetime.now() + timedelta(seconds=-1800)
            login_fail = {'type': 'login-fail', 'create_time': {'$gt': gap}, 'context': data.get('phone_or_email')}
            times = self.db.log.count_documents(login_fail)
            if times >= 20:
                return self.send_error_response(e.unauthorized, message='登录失败，请半小时后重试，或者申请重置密码')

            login_fail['create_time']['$gt'] = datetime.now() + timedelta(seconds=-60)
            times = self.db.log.count_documents(login_fail)
            if times >= 5:
                return self.send_error_response(e.unauthorized, message='登录失败，请一分钟后重试')

            # 尝试登录，成功后清除登录失败记录，设置为当前用户
            next_url = self.get_query_argument('next', '')
            self.login(self, data.get('phone_or_email'), data.get('password'), send_response='info=1' not in next_url)
            if 'info=1' in next_url:
                LoginApi.send_user_info(self)

        except DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def login(self, phone_or_email, password, report_error=True, send_response=True):
        user = self.db.user.find_one({'$or': [{'email': phone_or_email}, {'phone': phone_or_email}]})
        if not user:
            if report_error:
                self.add_op_log('login_no_user', context=phone_or_email)
                return send_response and self.send_error_response(e.no_user)
            return
        if user['password'] != helper.gen_id(password):
            if report_error:
                self.add_op_log('login_fail', context=phone_or_email)
                return send_response and self.send_error_response(e.incorrect_password)
            return

        # 清除登录失败记录
        ResetUserPasswordApi.remove_login_fails(self, phone_or_email)

        user['roles'] = user.get('roles', '')
        user['login_md5'] = helper.gen_id(user['roles'])
        self.current_user = user
        self.set_secure_cookie('user', json_util.dumps(user), expires_days=2)

        self.add_op_log('login_ok', context=phone_or_email + ': ' + user['name'], username=user['name'])
        info = 'login id=%s, name=%s, phone_or_email=%s, roles=%s'
        logging.info(info % (user['_id'], user['name'], phone_or_email, user['roles']))

        if send_response:
            self.send_data_response(user)
        return user

    @staticmethod
    def send_user_info(self):
        user = self.current_user
        url = self.get_query_argument('next').replace('?info=1', '').replace('&info=1', '')
        url += ('&' if '?' in url else '?') + urlencode(dict(
            sso_id=str(user['_id']), sso_name=user['name'], roles=user['roles']))
        self.send_data_response(dict(redirect=url))


class LogoutApi(BaseHandler):
    URL = '/api/user/logout'

    def post(self):
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
        try:
            data = self.get_request_data()
            rules = [
                (v.not_empty, 'name', 'password'),
                (v.not_both_empty, 'email', 'phone'),
                (v.is_name, 'name'),
                (v.is_email, 'email'),
                (v.is_phone, 'phone'),
                (v.is_password, 'password'),
                (v.not_existed, self.db.user, 'phone', 'email')
            ]
            if not options.testing and data.get('email') and self.config['email']['key'] not in ['', None, '待配置']:
                rules.append((v.not_empty, 'email_code'))
                rules.append((v.code_verify_timeout, self.db.verify, 'email', 'email_code'))
            if not options.testing and data.get('phone'):
                rules.append((v.not_empty, 'phone_code'))
                rules.append((v.code_verify_timeout, self.db.verify, 'phone', 'phone_code'))
            v.validate(data, rules, self)

            roles = self.config.get('role', {}).get('init', '')
            data['roles'] = '用户管理员' if not self.db.user.find_one() else roles  # 如果是第一个用户，则设置为用户管理员
            r = self.db.user.insert_one(dict(
                name=data['name'], email=data.get('email'), phone=data.get('phone'),
                gender=data.get('gender'), roles=data['roles'], img=data.get('img'),
                password=helper.gen_id(data['password']),
                create_time=datetime.now()
            ))
            data['_id'] = r.inserted_id
            data['login_md5'] = helper.gen_id(data['roles'])
            self.current_user = data
            self.set_secure_cookie('user', json_util.dumps(data), expires_days=2)

            message = '%s, %s, %s' % (data.get('email'), data.get('phone'), data['name'])
            self.add_op_log('register', context=message, username=data['name'])

            next_url = self.get_query_argument('next', '')
            if 'info=1' in next_url:
                LoginApi.send_user_info(self)
            else:
                self.send_data_response(data)

        except DbError as error:
            return self.send_db_error(error)


class ForgetPasswordApi(BaseHandler):
    URL = '/api/user/forget_pwd'

    def post(self):
        """将密码发送到注册时的邮箱或手机上"""

        data = self.get_request_data()
        rules = [
            (v.not_empty, 'name', 'phone_or_email'),
            (v.is_phone_or_email, 'phone_or_email'),
        ]
        v.validate(data, rules, self)

        phone_or_email = data['phone_or_email']
        user = self.db.user.find_one({'$or': [{'email': phone_or_email}, {'phone': phone_or_email}]})
        if not user:
            return self.send_error_response(e.no_user)
        if user['name'] != data['name']:
            return self.send_error_response(e.no_user, message='姓名不匹配')

        pwd = ResetUserPasswordApi.reset_pwd(self, user)
        if '@' in phone_or_email:
            r = SendUserEmailCodeApi.send_email(self, phone_or_email, """<html>
                <span style='font-size:16px;margin-right:10px'>密码：%s </span>
                <a href='http://%s/user/login'>返回登录页面</a>
                </html>
                """ % (pwd, self.config['site']['domain']))
        else:
            r = SendUserPhoneCodeApi.send_sms(self, phone_or_email, '密码: ' + pwd)

        if r:
            self.send_data_response()


class ChangeMyPasswordApi(BaseHandler):
    URL = '/api/user/my/pwd'

    def post(self):
        """ 修改我的密码 """
        try:
            data = self.get_request_data()
            rules = [
                (v.not_empty, 'password', 'old_password'),
                (v.not_equal, 'password', 'old_password'),
                (v.is_password, 'password')
            ]
            v.validate(data, rules, self)

            user = self.db.user.find_one(dict(_id=self.current_user['_id']))
            if user.get('password') != helper.gen_id(data['old_password']):
                return self.send_error_response(e.incorrect_old_password)
            update = dict(password=helper.gen_id(data['password']))
            self.db.user.update_one(dict(_id=self.current_user['_id']), {'$set': update})
            self.add_op_log('change_my_password', context=self.current_user['name'])
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class ChangeMyProfileApi(BaseHandler):
    URL = '/api/user/my/profile'

    def post(self):
        """ 修改我的个人信息，包括姓名、性别等 """
        try:
            data = self.get_request_data()
            rules = [
                (v.not_empty, 'name'),
                (v.not_both_empty, 'email', 'phone'),
                (v.is_name, 'name'),
                (v.is_email, 'email'),
                (v.is_phone, 'phone'),
                (v.not_existed, self.db.user, self.current_user['_id'], 'phone', 'email')
            ]
            v.validate(data, rules, self)

            fields, update = ['name', 'gender', 'email', 'phone'], dict()
            for field in fields:
                update[field] = data.get(field) or self.current_user[field]
                self.current_user[field] = update[field]

            r = self.db.user.update_one(dict(_id=self.current_user['_id']), {'$set': update})
            if not r.modified_count:
                return self.send_error_response(e.not_changed)

            self.set_secure_cookie('user', json_util.dumps(self.current_user), expires_days=2)
            self.add_op_log('change_my_profile', context=data.get('name'))
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class UploadUserAvatarApi(BaseHandler):
    URL = '/api/user/my/avatar'

    def post(self):
        """上传用户头像"""
        try:
            upload_img = self.request.files.get('img')
            img_name = str(self.current_user['_id']) + path.splitext(upload_img[0]['filename'])[-1]
            img_path = path.join(self.application.BASE_DIR, 'static', 'upload', 'avatar')
            img = 'upload/avatar/' + img_name
            with open(path.join(img_path, img_name), 'wb') as f:
                f.write(upload_img[0]['body'])
            self.db.user.update_one(dict(_id=self.current_user['_id']), {'$set': dict(img=img)})
            self.current_user['img'] = img
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class SendUserEmailCodeApi(BaseHandler):
    URL = '/api/user/email_code'

    def post(self):
        """用户注册时，发送邮箱验证码"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'email')]
            v.validate(data, rules, self)

            code = helper.random_code()
            if not self.send_email(self, data['email'], code):
                return self.send_error_response(e.email_send_failed)

            update = dict(code=code, stime=datetime.now())
            self.db.verify.find_one_and_update(dict(type='email', data=data['email']), {'$set': update}, upsert=True)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def send_email(self, receiver, code, subject="如是我闻古籍数字化平台"):
        """ email_list邮件列表，content邮件内容，subject发送标题 """

        try:
            content = code if '<html' in code else """<html>
                    <span style='font-size:16px;margin-right:10px'>您的验证码是：%s </span>
                    <a href='http://%s/user/register'>返回注册页面</a>
                    </html>
                    """ % (code, self.config['site']['domain'])

            msg = MIMEText(content, 'html', 'utf-8')
            account = self.config['email']['account']
            pwd = self.config['email']['key']
            host = self.config['email']['host']
            port = self.config['email'].get('port', 465)
            msg['From'] = account
            msg['to'] = receiver
            msg['Subject'] = Header(subject, 'utf-8')

            server = smtplib.SMTP_SSL(host, port)
            server.login(account, pwd)
            server.sendmail(account, receiver, msg.as_string())
            server.quit()
            return True

        except Exception as error:
            message = '发送邮件失败: [%s] %s' % (error.__class__.__name__, str(error))
            self.send_error_response(e.verify_failed, message=message)


class SendUserPhoneCodeApi(BaseHandler):
    URL = '/api/user/phone_code'

    def post(self):
        """用户注册时，发送手机验证码"""
        data = self.get_request_data()
        rules = [(v.not_empty, 'phone')]
        v.validate(data, rules, self)

        code = "%04d" % random.randint(1000, 9999)
        if not self.send_sms(self, data['phone'], code):
            return
        try:
            update = dict(code=code, stime=datetime.now())
            self.db.verify.find_one_and_update(dict(type='phone', data=data['phone']), {'$set': update}, upsert=True)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def send_sms(self, phone, code):
        """发送手机验证码"""
        try:
            account = self.config['phone']['accessKey']
            key = self.config['phone']['accessKeySecret']
            template_code = self.config['phone']['template_code']
            sign_name = self.config['phone']['sign_name']

            client = AcsClient(account, key, 'default')
            request = CommonRequest()
            request.set_domain('dysmsapi.aliyuncs.com')
            request.set_action_name('SendSms')
            request.set_version('2017-05-25')
            request.add_query_param('SignName', sign_name)
            request.add_query_param('PhoneNumbers', phone)
            request.add_query_param('TemplateCode', template_code)
            request.add_query_param('TemplateParam', '{"code": ' + code + '}')
            response = client.do_action_with_exception(request)
            response = response.decode()
            return response

        except Exception as error:
            message = '发送邮件失败: [%s] %s' % (error.__class__.__name__, str(error))
            self.send_error_response(e.verify_failed, message=message)


class UserlistApi(BaseHandler):
    URL = '/api/user/list'

    def post(self):
        """ 获取可访问某个任务类型的用户列表 """
        try:
            condition = dict()
            q = self.get_body_argument('q', '')
            if q:
                condition.update({'name': {'$regex': q}})
            size = 10
            cur_page = int(self.get_body_argument('page', 1))
            total_count = self.db.user.count_documents(condition)
            users = self.db.user.find(condition).sort('_id', 1).skip((cur_page - 1) * size).limit(size)
            users = [dict(id=str(u['_id']), text=u['name']) for u in list(users)]
            self.send_data_response(dict(results=list(users), pagination=dict(more=total_count > cur_page * size)))

        except Exception as error:
            return self.send_db_error(error)


class ChangeUserRoleApi(BaseHandler):
    URL = r'/api/user/admin/role'

    def post(self):
        """ 修改用户角色 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, '_id')]
            v.validate(data, rules, self)

            user = self.db.user.find_one(dict(_id=ObjectId(data['_id'])))
            if not user:
                return self.send_error_response(e.no_user, id=data['_id'])

            data['roles'] = data.get('roles') or ''
            r = self.db.user.update_one(dict(_id=ObjectId(data['_id'])), {'$set': dict(roles=data['roles'])})
            if not r.matched_count:
                return self.send_error_response(e.no_user)
            self.add_op_log('change_role', target_id=data['_id'], context='%s: %s' % (user['name'], data.get('roles')))
            self.send_data_response({'roles': data['roles']})

        except DbError as error:
            return self.send_db_error(error)


class ResetUserPasswordApi(BaseHandler):
    URL = r'/api/user/admin/reset_pwd'

    def post(self):
        """ 重置用户密码 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, '_id')]
            v.validate(data, rules, self)

            pwd = self.reset_pwd(self, data)
            if pwd:
                self.send_data_response({'password': pwd})

        except DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def reset_pwd(self, user):
        pwd = '%s%d' % (chr(random.randint(97, 122)), random.randint(10000, 99999))
        oid = ObjectId(user['_id'])
        r = self.db.user.update_one(dict(_id=oid), {'$set': dict(password=helper.gen_id(pwd))})
        if not r.matched_count:
            return self.send_error_response(e.no_user)

        user = self.db.user.find_one(dict(_id=oid))
        ResetUserPasswordApi.remove_login_fails(self, user['_id'])
        self.add_op_log('reset_password', target_id=user['_id'], context=user['name'])
        return pwd

    @staticmethod
    def remove_login_fails(self, context):
        time_gap = datetime.now() + timedelta(seconds=-3600)
        self.db.log.delete_many({'type': 'login_fail', 'create_time': {'$gt': time_gap}, 'context': context})


class DeleteUserApi(BaseHandler):
    URL = r'/api/user/admin/delete'

    def post(self):
        """ 删除用户 """
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_id', '_ids')]
            v.validate(data, rules, self)

            _ids = [data['_id']] if data.get('_id') else data['_ids']
            if str(self.current_user['_id']) in _ids:
                return self.send_error_response(e.cannot_delete_self)

            r = self.db.user.delete_many({'_id': {'$in': [ObjectId(i) for i in _ids]}})
            self.add_op_log('delete_user', target_id=_ids)
            self.send_data_response(dict(deleted_count=r.deleted_count))

        except DbError as error:
            return self.send_db_error(error)


class UserAddOrUpdateApi(BaseHandler):
    URL = '/api/user/admin'

    def post(self):
        """ 新增或修改 """
        try:
            data = self.get_request_data()
            rules = User.rules.copy()
            if data.get('_id'):
                user = self.db.user.find_one(dict(_id=ObjectId(data['_id'])))
                if not user:
                    self.send_error_response(e.no_object, message='没有找到用户')
                if not data.get('password'):
                    data['password'] = user['password']
                elif data['password'] != user['password']:
                    data['password'] = helper.gen_id(data['password'])
                rules.append((v.not_existed, self.db.user, ObjectId(data['_id']), 'phone', 'email'))
            else:
                data['password'] = helper.gen_id(data['password'])
                rules.append((v.not_existed, self.db.user, 'phone', 'email'))
            r = User.save_one(self.db, 'user', data, rules)
            if r.get('status') == 'success':
                self.add_op_log(('update_' if r.get('update') else 'add_') + 'user', context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except DbError as error:
            return self.send_db_error(error)
