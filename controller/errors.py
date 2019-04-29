#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc 定义后端API的错误码和数据库常用函数
@time: 2018/10/23
"""

need_login = 403, '尚未登录'
db_error = 10000, '数据库访问出错'
mongo_error = 20000, '文档库访问出错'
need_phone_or_email = 1001, '没有指定手机或邮箱'
need_password = 1002, '没有指定密码'
invalid_email = 1003, '邮箱格式错误'
no_user = 1004, '没有此账号'
incorrect_password = 1005, '密码错误'
unauthorized = 1006, '需要有相应权限才可执行本操作'
invalid_name = 1007, '姓名应为2~5个汉字，或3~20个英文字母（可含空格和-）'
invalid_password = 1008, '密码应为6至18位数字、字母和英文符号混合组成'
no_change = 1009, '没有发生改变'
incomplete = 1010, '信息不全'
invalid_parameter = 1011, '无效的参数'
user_exists = 1012, '账号已存在'
auth_changed = 1013, '授权信息已改变，请您重新登录'
no_object = 1014, '对象不存在或已删除'

task_locked = 2000, '本任务已被领走，请领取新的任务'
task_uncompleted = 2001, '您还有未完成的任务，请继续完成后再领取新的任务'
task_changed = 2002, '本任务的状态已改变'
