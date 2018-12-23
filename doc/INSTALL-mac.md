## 在 Mac 上的安装说明

1. 安装 Python 3.6+ 和 pip3

   本平台也可在 Python 2.7 下运行。

2. 安装 Python 依赖包（选择其一）：

   ```
   pip3 install -r requirements.txt
   sudo python3 -m pip install -r requirements.txt
   ```

3. 安装 MySQL 5.5+/MariaDB 10.3+ 数据库

   ```
   brew install mariadb
   mysql.server start
   mysql -u root -e 'create database tripitaka;'
   mysql -u root tripitaka < model/init.sql;
   ```
   如果数据库的用户和密码不是默认的root空密码，就修改 `app.yml` 中的数据库配置。
   每次重启操作系统后运行 `mysql.server start` 启动数据库，`mysql.server stop` 可关闭数据库。

4. 安装 MongoDB 文档数据库

   ```
   curl -O https://fastdl.mongodb.org/osx/mongodb-osx-ssl-x86_64-4.0.4.tgz
   tar -zxvf mongodb-osx-ssl-x86_64-4.0.4.tgz
   sudo mv mongodb-osx-ssl-x86_64-4.0.4/bin/* /usr/local/bin
   sudo mkdir -p /data/db
   sudo chown -R $(whoami) /data/db
   ```
   运行 `mongod` 启动数据库。

5. 启动网站服务

运行 `python3 main.py`，或者在 PyCharm 等集成开发环境中选中 main.py 调试。
在浏览器中打开本网站，进行登录或注册等操作。

如果提示端口被占用，可以按如下结束端口上的进程：
```sh
sudo lsof -i:8000
sudo kill -9 PID号
```
