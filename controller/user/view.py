#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""
from controller.model import User
from controller.base import BaseHandler
from controller.role import role_maps


class UserLoginHandler(BaseHandler):
    URL = '/user/login'

    def get(self):
        """ 登录页面 """
        self.render('user_login.html', next=self.get_query_argument('next', '/'))


class UserRegisterHandler(BaseHandler):
    URL = '/user/register'

    def get(self):
        """ 注册页面 """
        self.render('user_register.html', next=self.get_query_argument('next', '/'))


class UserProfileHandler(BaseHandler):
    URL = '/my/profile'

    def get(self):
        """ 个人中心 """
        self.render('my_profile.html')


class UsersAdminHandler(BaseHandler):
    URL = '/user/admin'

    def get(self):
        """ 用户管理页面 """
        fields = ['id', 'name', 'phone', 'email', 'gender', 'status', 'create_time']
        try:
            users = self.db.user.find({})
            users = [self.fetch2obj(r, User, fields=fields) for r in users]
            users.sort(key=lambda a: a.name)
            users = self.convert_for_send(users, trim=self.trim_user)
            self.add_op_log('get_users', context='取到 %d 个用户' % len(users))

        except Exception as e:
            return self.send_db_error(e, render=True)

        self.render('user_admin.html', users=users)

    @staticmethod
    def trim_user(r):
        r.image = 'imgs/' + {'': 'ava3.png', '女': 'ava.png', '男': 'ava2.png'}[r.gender or '']
        return r


class UserRolesHandler(BaseHandler):
    URL = '/user/role'

    def get(self):
        """ 角色管理页面 """
        fields = ['id', 'name', 'phone', 'roles']
        try:
            users = self.db.user.find({})
            users = [self.fetch2obj(r, User, fields=fields) for r in users]
            users.sort(key=lambda a: a.name)
            users = self.convert_for_send(users)
            self.add_op_log('get_users', context='取到 %d 个用户' % len(users))

        except Exception as e:
            return self.send_db_error(e, render=True)

        roles = dict(role_maps)
        roles.pop('单元测试用户')
        roles.pop('访客')
        self.render('user_role.html', users=users, roles=list(roles.keys()))


class UserStatisticHandler(BaseHandler):
    URL = '/user/statistic'

    def get(self):
        """ 人员管理-数据管理页面 """
        fields = ['id', 'name', 'phone']
        try:
            users = self.db.user.find({})
            users = [self.fetch2obj(r, User, fields=fields) for r in users]
            users.sort(key=lambda a: a.name)
            users = self.convert_for_send(users)
            for r in users:
                # 切分校对数量、切分审定数量、文字校对数量、文字审定数量、文字难字数量、文字反馈数量、格式标注数量、格式审定数量
                r.update(dict(cut_proof_count=0, cut_review_count=0,
                              text_proof_count=0, text_review_count=0,
                              text_difficult_count=0, text_feedback_count=0,
                              fmt_proof_count=0, fmt_review_count=0))
            self.add_op_log('get_users_completed')

        except Exception as e:
            return self.send_db_error(e, render=True)

        self.render('user_statistic.html', users=users)


