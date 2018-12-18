# 大藏经古籍数字化平台

## 前端改版

- 参考[前端模板语法][templates]修改网页代码，主要使用`{% if/for %}`、`{{ py_expr }}`，
  例如 `{{ user.get('name') }}` 得到用户昵称。
  
  常用变量见 `controller/base.py render()` 和相应的响应Handler中的参数。

- 使用 `{% include %}` 提取公共网页部分，例如 `_base_css.html`、`_base_js.html`、`_base_meta.html`。

- 可调用 `getApi`、`postApi` 函数调用后端接口，执行操作和填充页面数据。

- 可使用 `showError`、`showSuccess`、`decodeJSON` 等常用函数进行消息显示和数据转换。

## 安装

本平台需要 Python 3.6+、MySQL 5.5+/MariaDB 10.3+、MongoDB，请参考下面的说明安装和部署。

- [INSTALL-linux.md](INSTALL-linux.md)
- [INSTALL-mac.md](INSTALL-mac.md)
- [INSTALL-win.md](INSTALL-win.md)

## 参考资料

- [Bootstrap 3 中文文档](https://v3.bootcss.com)
- [Tornado 官方文档中文版](https://tornado-zh.readthedocs.io/zh/latest/)
- [Tornado 前端模板语法]()
- [Introduction to Tornado 中文版](http://demo.pythoner.com/itt2zh/)
- [MongoDB 数据库开发](http://demo.pythoner.com/itt2zh/ch4.html)

[templates]: https://tornado-zh.readthedocs.io/zh/latest/guide/templates.html
