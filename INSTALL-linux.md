## 在 Linux 上的安装说明

### 1. 安装 Python 3.6+ 和 pip3

```
sudo yum install -y gcc zlib*
sudo yum install -y zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel
wget http://cdn.npm.taobao.org/dist/python/3.6.5/Python-3.6.5.tgz
tar -zxvf Python-3.6.5.tgz
cd Python-3.6.5/
./configure --prefix=/usr/local/python3 --with-ssl --enable-optimizations
make && sudo make install
sudo ln -s /usr/local/python3/bin/python3 /usr/bin/python3
sudo ln -s /usr/local/python3/bin/pip3 /usr/bin/pip3
```

如果提示 `wget` 工具不存在，可换为 `curl -O ` 或安装 wget。

### 2. 安装 Python 依赖包

```
cd this_project
sudo pip3 install --upgrade pip
sudo pip3 install -r requirements.txt
```

### 3. 安装 MySQL 5.5+/MariaDB 10.3+ 数据库

```
sudo yum -y install mariadb mariadb-server
sudo systemctl enable mariadb
sudo systemctl start mariadb
mysql_secure_installation
mysql -uroot -p
create database tripitaka;
quit
mysql -u root -p tripitaka < model/init.sql;
```

将输入的 root 密码记到 `app.yml` 的 `database.password` 中。

### 4. 安装 MongoDB 文档数据库

```
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-4.0.4.tgz
tar -zxvf mongodb-linux-x86_64-4.0.4.tgz
sudo mv mongodb-linux-x86_64-4.0.4/bin/* /usr/local/bin
sudo mkdir -p /data/db
sudo chown -R $(whoami) /data/db
mkdir log
mongod -logpath log/mongo.log -logappend -fork
```

如果是在 Ubuntu、Debian、RHEL 或 SUSE 上安装，可将上面的地址改为 [官网][mongodb-down] 上的相应下载地址。

[mongodb-down]: https://www.mongodb.com/download-center/community

### 5. 启动网站服务

注：如果是在个人电脑上开发和测试，则不需要配置下面的参数，直接运行 `python3 main.py` 即可。

- 如果要部署的云服务器有HTTPS证书和私钥文件，可以复制到本项目的目录下，
  在 `app.yml` 的 `https` 中指定这两个文件，将 `port` 改为 443。

- 如果服务器不需要支持 HTTPS，则将 `start.sh` 中的 `--port` 处和 `app.yml` 的`port` 处改为实际的端口号。

- 在 `app.yml` 中指定域名 `domain`。

- 然后启动网站服务：
  ```
  mkdir log
  sh start.sh
  ```
  如果提示端口被占用，可以按如下结束端口上的进程：
  ```sh
  sudo lsof -i:8000
  sudo kill -9 PID号
  ```
