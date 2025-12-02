# 数据库
``` bash
# 连接数据句
mysql -u root -p
```

## 创建数据库

``` sql
-- 创建数据库
CREATE DATABASE bettafish_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权
CREATE USER 'jfzhou1'@'localhost' IDENTIFIED BY '19941010';

-- 授予权限
GRANT ALL PRIVILEGES ON bettafish_db.* TO 'jfzhou1'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;

-- 退出
quit;
```

## 验证
``` bash
mysql -u jfzhou1 -p -D bettafish_db
```

## 初始化数据库
``` bash
# 在MindSpider目录下
cd MindSpider

# 初始化数据库
python main.py --init-db

# 或运行完整初始化
python main.py --setup
```