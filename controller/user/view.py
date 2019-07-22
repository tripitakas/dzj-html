#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""
from controller.base import BaseHandler
from controller.role import assignable_roles
import math
import logging


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
    URL = '/user/my/profile'

    def get(self):
        """ 个人中心 """
        self.render('my_profile.html')


class UsersAdminHandler(BaseHandler):
    URL = '/user/admin'

    def get(self):
        """ 用户管理页面 """
        try:
            item_count = self.db.user.count_documents({})
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            cur_page = math.ceil(item_count / page_size) if math.ceil(item_count / page_size) < cur_page else cur_page
            users = list(self.db.user.find().sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            logging.info('%d users' % len(users))
        except Exception as e:
            return self.send_db_error(e, render=True)

        pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
        self.render('user_admin.html', users=users, pager=pager)


class UserRolesHandler(BaseHandler):
    URL = '/user/role'

    def get(self):
        """ 角色管理页面 """
        try:
            item_count = self.db.user.count_documents({})
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            cur_page = math.ceil(item_count / page_size) if math.ceil(item_count / page_size) < cur_page else cur_page
            users = list(self.db.user.find().sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            logging.info('%d users' % len(users))
        except Exception as e:
            return self.send_db_error(e, render=True)

        pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
        self.render('user_role.html', users=users, roles=assignable_roles, pager=pager)


class UserStatisticHandler(BaseHandler):
    URL = '/user/statistic'

    def get(self):
        """ 人员管理-数据管理页面 """
        try:
            item_count = self.db.user.count_documents({})
            page_size = int(self.config['pager']['page_size'])
            cur_page = int(self.get_query_argument('page', 1))
            cur_page = math.ceil(item_count / page_size) if math.ceil(item_count / page_size) < cur_page else cur_page
            users = list(self.db.user.find().sort('_id', 1).skip((cur_page - 1) * page_size).limit(page_size))
            logging.info('%d users' % len(users))
            for r in users:
                # 切分校对数量、切分审定数量、文字校对数量、文字审定数量、文字难字数量、文字反馈数量、格式标注数量、格式审定数量
                r.update(dict(cut_proof_count=0, cut_review_count=0, text_proof_count=0, text_review_count=0,
                              text_difficult_count=0, text_feedback_count=0, fmt_proof_count=0,
                              fmt_review_count=0))
        except Exception as e:
            return self.send_db_error(e, render=True)

        pager = dict(cur_page=cur_page, item_count=item_count, page_size=page_size)
        self.render('user_statistic.html', users=users, pager=pager)
