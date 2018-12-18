## 在 Windows 上的安装说明

### 1. 安装 Python 3.6+ 和 pip3

可在 [官网](https://www.python.org/downloads/) 下载 Python 3.6或3.7 的安装程序，
安装时勾选 “添加Python到PATH” 选项以便可在命令行运行Python。

### 2. 安装 Python 依赖包

```
cd this_project
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 安装 MySQL 5.5+/MariaDB 10.3+ 数据库

可在 [官网](https://downloads.mariadb.org/) 下载安装程序，如果设置了root密码就记到 `app.yml` 的 `database.password` 中。

在“开始”程序菜单中打开“MySQL Client”，执行下列命令：
```
create database tripitaka;
quit
mysql -u root -p tripitaka < this_project\model\init.sql
```

### 4. 安装 MongoDB 文档数据库

- 从 [官网](https://www.mongodb.com/download-center#community) 下载安装程序，如果是32位操作系统就选择3.2版本。

- 将安装目录下 `bin` 目录添加到 `PATH` 环境变量，或者在下面命令中带上`bin`目录。
- 在数据盘（例如C:）创建 `data`、`data\db` 文件夹。
- 在命令行中执行：
  ```
  mongod --dbpath c:\data\db
  ```
  如果提示默认的 `storageEngine` 不支持，则按照提示添加参数，例如 `--storageEngine=mmapv1`。

### 5. 启动网站服务

运行 `python main.py --debug=0`，在浏览器中打开 [localhost:8000](http://localhost:8000)。

如果提示端口被占用，可以按如下结束端口上的进程：
```sh
netstat -ano | findstr 8000
taskkill -F -PID PID号
```
