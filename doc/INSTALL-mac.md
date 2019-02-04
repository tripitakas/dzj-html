## 在 Mac 上的安装说明

1. 安装 Python 3.6+ 和 pip3

2. 安装 Python 依赖包（选择其一）：

   ```
   pip3 install -r requirements.txt
   sudo python3 -m pip install -r requirements.txt
   ```

3. 安装 MongoDB 文档数据库（可直接使用远程数据库）

   ```
   curl -O https://fastdl.mongodb.org/osx/mongodb-osx-ssl-x86_64-4.0.4.tgz
   tar -zxvf mongodb-osx-ssl-x86_64-4.0.4.tgz
   sudo mv mongodb-osx-ssl-x86_64-4.0.4/bin/* /usr/local/bin
   sudo mkdir -p /data/db
   sudo chown -R $(whoami) /data/db
   ```
   运行 `mongod` 启动数据库。
   
   如果使用远程数据库则不需要在本地安装 MongoDB：在 `app.yml` （首次启动网站服务可得到，或从 `_app.yml` 复制得到）中的`database`中
   设置远程数据库的地址和密码等相应参数。

4. 启动网站服务

运行 `python main.py`，或者在 PyCharm 等集成开发环境中选中 main.py 调试。
在浏览器中打开本网站，进行登录或注册等操作，注册的第一个用户将是管理员。

如果提示端口被占用，可以按如下结束端口上的进程：
```sh
sudo lsof -i:8000
sudo kill -9 PID号
```
