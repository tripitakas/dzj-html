#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc 定义后端API的错误码和数据库常用函数
@time: 2018/10/23
"""

need_login = 403, '尚未登录'

db_error = 10000, '数据库访问出错'
mongo_error = 20000, '文档库访问出错'

mutiple_errors = 1000, '多个数据校验错误'
not_allowed_empty = 1001, '%s不允许为空'
not_allowed_both_empty = 1002, '%s和%s不允许同时为空'
invalid_name = 1003, '姓名应为2~5个汉字，或3~20个英文字母（可含空格和-）'
invalid_phone = 1004, '手机号码格式有误'
invalid_email = 1005, '邮箱格式有误'
invalid_password = 1006, '密码应为6至18位由数字、字母和英文符号组成的字符串，不可以为纯数字或纯字母'
invalid_range = 1007, '%s数据范围应为[%s, %s]'
need_phone_or_email = 1008, '没有指定手机或邮箱'
need_password = 1009, '没有指定密码'
invalid_phone_or_email = 1010, '手机或邮箱格式有误'
not_allow_equal = 1011, '%s和%s一致'
not_equal = 1012, '%s和%s不一致'
record_existed = 1013, '%s已存在'
mutiple_record = 1014, '%s存在多条记录'

no_user = 2001, '没有此账号'
user_existed = 2002, '账号已存在'
incorrect_password = 2003, '密码错误'
incorrect_old_password = 2012, '原始密码错误'
unauthorized = 2004, '没有权限'
auth_changed = 2005, '授权信息已改变，请您重新登录'
no_change = 2006, '没有发生改变'
incomplete = 2007, '信息不全'
invalid_parameter = 2008, '无效的参数'
no_object = 2009, '对象不存在或已删除'
cannot_delete_self = 2012, '不能删除自己'

task_locked = 3000, '本任务(%s)已被领走，请领取新的任务'
task_uncompleted = 3001, '您还有未完成的任务(%s)，请继续完成后再领取新的任务'
task_changed = 3002, '本任务的状态已改变'
