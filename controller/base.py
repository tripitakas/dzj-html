#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 后端API响应的基础函数和类
@author: Zhang Yungui
@time: 2018/6/23
"""

import logging
import re
import traceback
from datetime import datetime

from bson.errors import BSONError
from pyconvert.pyconv import convertJSON2OBJ, convert2JSON
from pymongo.errors import PyMongoError
from pymysql.constants import ER
from pymysql.cursors import DictCursor
from pymysql.err import MySQLError, Warning, ProgrammingError
from tornado.escape import json_decode, json_encode, basestring_type
from tornado.options import options
from tornado.web import RequestHandler
from tornado_cors import CorsMixin

from controller import errors
from model.user import User, authority_map, ACCESS_ALL


def my_framer():
    f0 = f = old_framer()
    if f is not None:
        f = f.f_back
        while re.search(r'(web|base)\.py|logging', f.f_code.co_filename):
            f0 = f
            f = f.f_back
    return f0


old_framer = logging.currentframe
logging.currentframe = my_framer

MongoError = (PyMongoError, BSONError)
DbError = (PyMongoError, BSONError, MySQLError)


def fetch_authority(user, record):
    """ 从记录中读取权限字段值 """
    authority = None
    if record:
        items = [authority_map[f] for f in list(authority_map.keys()) if record.get(f)]
        authority = ','.join(sorted(items, key=lambda a: ACCESS_ALL.index(a) if a in ACCESS_ALL else -1))
    if user:
        user.authority = authority or '普通用户'
    return authority


def convert_bson(r):
    if not r:
        return r
    for k, v in (r.items() if isinstance(r, dict) else enumerate(r)):
        if type(v) == datetime:
            r[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(v, dict):
            convert_bson(v)
    if 'update_time' not in r and 'create_time' in r:
        r['update_time'] = r['create_time']
    if '_id' in r:
        r['id'] = str(r.pop('_id'))
    return r


def convert2obj(cls, json_obj):
    """ 将JSON对象转换为指定模型类的对象 """
    if isinstance(json_obj, dict):
        for k, v in list(json_obj.items()):
            if v is None or v == str:
                json_obj.pop(k)
    obj = convertJSON2OBJ(cls, json_obj)
    fields = [f for f in cls.__dict__.keys() if f[0] != '_']
    for f in fields:
        if f not in obj.__dict__:
            obj.__dict__[f] = None
    return obj


def execute(cursor, query, args=None):
    query = cursor.mogrify(query, args)
    try:
        return cursor.execute(query)
    except ProgrammingError:
        logging.warning(query)
        raise


class BaseHandler(CorsMixin, RequestHandler):
    """ 后端API响应类的基类 """
    CORS_HEADERS = 'Content-Type,Host,X-Forwarded-For,X-Requested-With,User-Agent,Cache-Control,Cookies,Set-Cookie'
    CORS_CREDENTIALS = True

    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*' if options.debug else self.application.site['domain'])
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Access-Control-Allow-Headers', self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self._get_methods())
        self.set_header('Access-Control-Allow-Credentials', 'true')

    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)
        self.authority = ''
        self.db = self.application.db

    def get_current_user(self):
        if 'Access-Control-Allow-Origin' not in self._headers:
            self.write({'code': 403, 'error': 'Forbidden'})
            return self.finish()

        user = self.get_secure_cookie('user')
        try:
            user = user and convert2obj(User, json_decode(user))
            self.authority = user and user.authority or ''
            return user or None
        except TypeError as e:
            print(user, str(e))

    def update_login(self, conn=None):
        """ 更新内存中的当前用户及其权限信息 """
        if not self.current_user:
            return False
        if not conn:
            with self.connection as conn:
                return self.update_login(conn)

        fields = ['email'] + list(authority_map.keys())
        sql = 'SELECT {0} FROM t_user a,t_authority b WHERE a.id=b.user_id and a.id=%s'.format(','.join(fields))
        with conn.cursor(DictCursor) as cursor:
            execute(cursor, sql, (self.current_user.id,))
            old_user = self.fetch2obj(cursor.fetchone(), User, fetch_authority)
            if old_user:
                user = self.current_user
                user.authority = old_user.authority
                for k, v in list(user.__dict__.items()):
                    if v is None or v == str:
                        user.__dict__.pop(k)
                self.set_secure_cookie('user', json_encode(self.convert2dict(user)))
            else:
                self.current_user.authority = ''
                raise Warning(1, '需要重新登录或注册')
        self.authority = self.current_user.authority
        return True

    def render(self, template_name, **kwargs):
        kwargs['authority'] = self.current_user.authority if self.current_user else ''
        kwargs['currentUserId'] = self.current_user.id if self.current_user else ''
        kwargs['protocol'] = self.request.protocol
        kwargs['debug'] = self.application.settings['debug']
        kwargs['site'] = dict(self.application.site)
        super(BaseHandler, self).render(template_name, dumps=lambda p: json_encode(p), **kwargs)

    @staticmethod
    def _trim_obj(obj, param_type):
        if param_type not in [dict, str, int, float]:
            fields = [f for f in param_type.__dict__.keys() if f[0] != '_']
            for f in list(obj.__dict__):
                if f not in fields and '__' not in f:
                    del obj.__dict__[f]
            for f in fields:
                if f not in obj.__dict__:
                    obj.__dict__[f] = None
                elif isinstance(obj.__dict__[f], str):
                    obj.__dict__[f] = obj.__dict__[f].strip()

    def get_body_obj(self, param_type):
        """
        从请求内容的 data 属性解析出指定模型类的一个或多个对象.
        客户端的请求需要在请求体中包含 data 属性，例如 $.ajax({url: url, data: {data: some_obj}...
        :param param_type: 模型类或dict
        :return: 指定模型类的对象，如果 data 属性值为数组则返回对象数组
        """

        def str2obj(text):
            if type(text) == dict:
                for k, v in list(text.items()):
                    if v is None:
                        text.pop(k)
            return convert2obj(param_type, text)

        if 'data' not in self.request.body_arguments:
            body = json_decode(self.request.body)['data']
        else:
            body = self.get_body_argument('data')
        if param_type == str:
            param_obj = body
        elif param_type == dict:
            param_obj = json_decode(body or '{}')
            return param_obj
        else:
            try:
                body = json_decode(body or '{}')
                if type(body) == list:
                    param_obj = [str2obj(p) for p in body]
                else:
                    param_obj = str2obj(body)
            except ValueError:
                logging.error(body)
                return

        if type(param_obj) == list:
            [self._trim_obj(p, param_type) for p in param_obj]
        else:
            self._trim_obj(param_obj, param_type)
        return param_obj

    @staticmethod
    def convert2dict(obj):
        """ 将模型类的对象转为 dict 对象，以便输出到客户端 """
        filter_attr = obj.__dict__
        data = dict()
        for v in filter_attr:
            d = getattr(obj, v)
            data[v] = d
        return data

    def convert_for_send(self, response, trim=None):
        """ 将包含模型对象的API响应内容转换为原生对象(dict或list) """
        if isinstance(response, list):
            response = [self.convert_for_send(r, trim) for r in response]
        elif hasattr(response, '__dict__'):
            dup = response.__class__()
            for f, v in response.__dict__.items():
                dup.__dict__[f] = v
            if callable(trim):
                trim(dup)
            for f, v in list(dup.__dict__.items()):
                if v is None or v == str:
                    del dup.__dict__[f]
            response = convert2JSON(dup)
        return response

    def send_response(self, response=None, trim=None):
        """ 发送并结束API响应内容 """
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        response = self.convert_for_send({'code': 200} if response is None else response, trim)
        if not isinstance(response, dict):
            response = json_encode({'items': response} if isinstance(response, list) else response)
        self.write(response)
        self.finish()

    def send_error(self, status_code=500, **kwargs):
        """ 发送并结束API异常响应消息 """
        if isinstance(status_code, tuple):
            status_code, message = status_code
            if 'reason' in kwargs and kwargs['reason'] != message:
                message += ': ' + kwargs['reason']
            kwargs['reason'] = message
        self.write_error(status_code, **kwargs)

    def write_error(self, status_code, **kwargs):
        reason = kwargs.get('reason') or self._reason
        reason = reason if reason != 'OK' else '无权访问' if status_code == 403 else '后台服务出错'
        logging.error('%d %s [%s %s]' % (status_code, reason,
                                         self.current_user and self.current_user.name, self.get_ip()))
        if not self._finished:
            self.set_header('Content-Type', 'application/json; charset=UTF-8')
            self.write({'code': status_code, 'error': reason})
            self.finish()

    @property
    def connection(self):
        return auto_commit(self, self.application.open_connection())

    def send_db_error(self, e):
        code = type(e.args) == tuple and len(e.args) > 1 and e.args[0] or 0
        reason = re.sub(r'[<{;:].+$', '', e.args[1]) if code else re.sub(r'\(0.+$', '', str(e))
        if not code and '[Errno' in reason and isinstance(e, MongoError):
            code = int(re.sub(r'^.+Errno |\].+$', '', reason))
            reason = re.sub(r'^.+\]', '', reason)
            return self.send_error(errors.mongo_error[0] + code,
                                   reason='无法访问文档库' if code in [61] else '%s(%s)%s' % (
                                       errors.mongo_error[1], e.__class__.__name__, ': ' + (reason or '')))
        if code:
            logging.error(e.args[1])
        if 'InvalidId' == e.__class__.__name__:
            code, reason = 1, errors.no_object[1]
        if code not in [2003, ER.ACCESS_DENIED_ERROR, 1]:
            traceback.print_exc()
        default_error = errors.mongo_error if isinstance(e, MongoError) else errors.db_error
        self.send_error(default_error[0] + code, for_yield=True,
                        reason='无法连接数据库' if code in [2003, ER.ACCESS_DENIED_ERROR] else '%s(%s)%s' % (
                            default_error[1], e.__class__.__name__, ': ' + (reason or '')))

    @staticmethod
    def insert_sql(table, kwargs):
        """
        得到 INSERT 语句
        :param table: 表名
        :param kwargs: 字段名与值的字典对象
        :return: SQL语句, 额外的字符串参数（在 execute 中使用）
        """
        extra = [v for v in kwargs.values() if v != str and isinstance(v, basestring_type)]
        values = ['INET_ATON(%s)' if k == 'ip' else
                  '%s' if v != str and isinstance(v, basestring_type) else
                  'null' if v is None or v == str else str(v) for k, v in kwargs.items()]
        return 'INSERT INTO {0}({1}) VALUES({2})'.format(table, ','.join(kwargs.keys()), ','.join(values)), extra

    @staticmethod
    def select_sql(fields, from_where):
        """
        得到 SELECT 语句
        :param fields: 要读取的数据库字段的列表或元组，可为字段名指定模型属性名，例如 ('user_id=id', 'name')
        :param from_where: 包含 FROM 和 WHERE 的子句
        :return: SQL语句
        """
        return 'SELECT {0} {1}'.format(','.join(f.split('=')[0] for f in fields), from_where)

    @staticmethod
    def fetch2obj(record, cls, extra=None):
        """
        将从数据库取到(fetchall、fetchone)的记录字典对象转为模型对象
        :param record: 数据库记录，字典对象
        :param cls: 模型对象的类
        :param extra: 额外字段的读取函数
        :return: 模型对象
        """
        if record:
            obj = {}
            fields = set(cls.__dict__.keys()) & set(record.keys())
            for f in fields:
                value = record[f]
                if type(value) == datetime:
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                if value is not None:
                    obj[f] = value
            obj = convert2obj(cls, obj)
            if obj and extra:
                extra(obj, record)
            return obj

    def get_ip(self):
        ip = self.request.headers.get('x-forwarded-for') or self.request.remote_ip
        return ip and re.sub(r'^::\d$', '', ip[:15]) or '127.0.0.1'

    def add_op_log(self, cursor, op_type, file_id=None, context=None):
        logging.info('%s,file_id=%s,context=%s' % (op_type, file_id, context))
        sql = self.insert_sql('t_op_log', dict(type=op_type,
                                               user_id=self.current_user and self.current_user.id,
                                               file_id=file_id or None,
                                               context=context and context[:80],
                                               create_time=errors.get_date_time(),
                                               ip=self.get_ip()))
        if cursor:
            return execute(cursor, *sql)
        with self.connection as conn:
            with conn.cursor() as cursor:
                return execute(cursor, *sql)


class auto_commit(object):
    def __init__(self, handler, conn):
        self.handler = handler
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, err, exc_val, exc_tb):
        if err:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()
