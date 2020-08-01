#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 登录和注册
@time: 2018/6/23
"""
from controller import auth
from controller import helper as h
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
        self.render('user_profile.html')


class UsersAdminHandler(BaseHandler, User):
    URL = '/user/admin'

    page_title = '用户管理'
    search_tips = '请搜索用户名、手机和邮箱'
    search_fields = ['name', 'email', 'phone']
    table_fields = [dict(id=f['id'], name=f['name']) for f in User.fields if f['id'] not in ['password']]
    info_fields = ['name', 'gender', 'email', 'phone', 'password']
    update_fields = [dict(id=f['id'], name=f['name'], input_type=f.get('input_type', 'text'), options=f.get('options'))
                     for f in User.fields if f['id'] not in ['img', 'create_time', 'updated_time']]
    operations = [  # 列表包含哪些批量操作
        {'operation': 'btn-add', 'label': '新增用户'},
        {'operation': 'bat-remove', 'label': '批量删除'},
    ]
    img_operations = ['config']
    actions = [  # 列表单条记录包含哪些操作
        {'action': 'btn-update', 'label': '更新'},
        {'action': 'btn-remove', 'label': '删除'},
        {'action': 'btn-reset-pwd', 'label': '重置密码'},
    ]

    @staticmethod
    def format_value(value, key=None, doc=None):
        """ 格式化page表的字段输出"""
        if key == 'img':
            ava = 'imgs/ava%s.png' % ({'男': 1, '女': 2}.get(doc.get('gender')) or 3)
            return '<img src="/static/%s" class="thumb-md img-circle" />' % (value or ava)
        return h.format_value(value, key, doc)

    def get(self):
        """ 用户管理页面 """
        try:
            kwargs = self.get_template_kwargs()
            docs, pager, q, order = self.find_by_page(self)
            self.render('user_list.html', docs=docs, pager=pager, q=q, order=order,
                        format_value=self.format_value, **kwargs)

        except Exception as error:
            return self.send_db_error(error)


class UserRolesHandler(BaseHandler, User):
    URL = '/user/role'

    def get_template_kwargs(self, fields=None):
        kwargs = super().get_template_kwargs(fields)
        kwargs['operations'] = []
        kwargs['img_operations'] = []
        return kwargs

    def get(self):
        """ 角色管理页面 """
        try:
            kwargs = self.get_template_kwargs()
            docs, pager, q, order = self.find_by_page(self)
            init_roles = self.prop(self.config, 'role.init')
            disabled_roles = self.prop(self.config, 'role.disabled', [])
            roles = [r for r in auth.get_assignable_roles() if r not in disabled_roles]
            if '系统管理员' in self.current_user['roles'] and '系统管理员' not in roles:
                roles.append('系统管理员')

            self.render('user_role.html', docs=docs, pager=pager, q=q, order=order, roles=roles,
                        init_roles=init_roles, disabled_roles=disabled_roles, **kwargs)

        except Exception as error:
            return self.send_db_error(error)
