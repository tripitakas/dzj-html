# 大藏经古籍数字化平台（生产版）

[![Build Status](https://travis-ci.org/tripitakas/tripitaka-web.svg?branch=master)](https://travis-ci.org/tripitakas/tripitaka-web)
[![Coverage](https://codecov.io/gh/tripitakas/tripitaka-web/branch/master/graph/badge.svg)](https://codecov.io/gh/tripitakas/tripitaka-web)


## Wiki在线文档

- [URL和API介绍](https://github.com/tripitakas/tripitaka-web/wiki/URL-and-API-Introduction)
- [任务流介绍](https://github.com/tripitakas/tripitaka-web/wiki/Task-Flow-Introduction)
- [分层权限机制](https://github.com/tripitakas/tripitaka-web/wiki/auth)
- [RBAC-基于角色的访问控制](https://github.com/tripitakas/tripitaka-web/wiki/RBAC)
- [前后端数据JSON格式约定](https://github.com/tripitakas/tripitaka-web/wiki/JSON-communication-format)

## 前端改版

- 参考[前端模板语法][templates]修改网页代码，主要使用`{% if/for %}`、`{{ py_expr }}`。
  
  常用变量见 `controller/base.py render()` 和相应的响应Handler中的参数。
  在网页中可使用`{{dumps(your_obj)}}` 或 `{{your_obj}}`显示数据结构辅助编码。

- 使用 `{% include %}` 提取公共网页部分，例如 `com/_base_css.html`、`com/_base_js.html`。

- 可调用 `getApi`、`postApi` 函数调用后端接口，执行操作和填充页面数据。

- 可使用 `showError`、`showSuccess`、`decodeJSON` 等常用函数进行消息显示和数据转换。

- 在网页中要将python对象转为js对象时，可以用 `dumps` 函数先将python对象转为JSON串（用单引号括起来，例如 `modify('{{dumps(p)}}')` ），
  然后在js代码中使用 `decodeJSON` 转为 js对象。

- 使用 webfont 代替按钮图标图片。网站所有的图标放在`static/assets/my-icon`下，
  点击[demo.html](static/assets/my-icon/demo.html)可以看到有哪些可用的图标。
  另一个图标来源是bootstrap自带的glyphicon。

## 安装

本平台需要 Python 3.6+、MongoDB(可用远程数据库)，请参考下面的说明安装和部署。

- [INSTALL-linux.md](doc/INSTALL-linux.md)
- [INSTALL-mac.md](doc/INSTALL-mac.md)
- [INSTALL-win.md](doc/INSTALL-win.md)

使用 `add_pages.py` 批量添加页面切分数据，可改变参数为实际页面的路径，或者选择下面某一种方式使用示例数据：

```
sh meta/decompress.sh
python3 utils/add_pages.py --reorder=v2
python3 utils/import_meta.py
```

如需推送数据到远程数据库，可在uri参数中指定服务器地址、用户名、密码：
```
python3 utils/add_pages.py --db_name=tripitaka --uri=mongodb://user:password@server:port
```

## 测试

本项目可采用测试驱动开发(TDD)模式实现后端接口：

```
pip install -r tests/requirements.txt
sh meta/decompress.sh
python3 utils/add_pages.py --db_name=tripitaka_test --reset=1 --reorder=v2
python3 utils/import_meta.py --db_name=tripitaka_test --reset=1
python3 utils/gen_chars.py --db_name=tripitaka_test --reset=1
python3 run_tests.py 或选中测试用例文件调试
```

在 `tests` 下编写测试用例，然后在 `controller.views` 或 `controller.api` 中实现后端接口。

使用 `add_pages.py` 批量添加页面切分数据，可改变参数为实际页面的路径。

如果需要单独多次调试某个用例，可将 `run_tests.py` 中的 `test_args += ['-k test_` 行注释去掉，
改为相应的测试用例名，在用例或API响应类中设置断点调试。

## 参考资料

- [项目术语表](doc/glossary.md)

- [Bootstrap 3 中文文档](https://v3.bootcss.com)
- [Tornado 官方文档中文版](https://tornado-zh.readthedocs.io/zh/latest/)
- [Tornado 前端模板语法][templates]
- [Introduction to Tornado 中文版](http://demo.pythoner.com/itt2zh/)
- [MongoDB 数据库开发](http://demo.pythoner.com/itt2zh/ch4.html)
- [MongoDB 官方文档](http://api.mongodb.com/python/current/index.html)
- [MongoDB 查询操作符](https://docs.mongodb.com/manual/reference/operator/query/)
- [Raphael 图形库文档](http://dmitrybaranovskiy.github.io/raphael/reference.html)

[templates]: https://tornado-zh.readthedocs.io/zh/latest/guide/templates.html
