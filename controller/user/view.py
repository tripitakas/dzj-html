#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""
from controller import auth
from controller.user.user import User
from controller.base import BaseHandler


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
    search_tips = '请搜索用户名、手机和邮箱'
    operations = [
        {'operation': 'btn-add', 'label': '新增用户'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]

    def get(self):
        """ 用户管理页面 """
        try:
            kwargs = User.get_page_kwargs()
            kwargs['operations'] = self.operations
            kwargs['search_tips'] = self.search_tips
            docs, pager, q, order = User.find_by_page(self)
            self.render('user_list.html', docs=docs, pager=pager, q=q, order=order, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class UserRolesHandler(BaseHandler):
    URL = '/user/admin/role'
    operations = []
    search_tips = '请搜索用户名'

    def get(self):
        """ 角色管理页面 """
        try:
            kwargs = User.get_page_kwargs()
            kwargs['operations'] = self.operations
            kwargs['search_tips'] = self.search_tips
            docs, pager, q, order = User.find_by_page(self)
            init_roles = self.prop(self.config, 'role.init')
            disabled_roles = self.prop(self.config, 'role.disabled', [])
            roles = [r for r in auth.get_assignable_roles() if r not in disabled_roles]

            self.render('user_role.html', docs=docs, pager=pager, q=q, order=order, roles=roles,
                        init_roles=init_roles, disabled_roles=disabled_roles, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
