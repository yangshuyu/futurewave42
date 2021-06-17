# replace

### 需要配置几个环境变量
    
    export MODE='xxx' (PRODUCTION 或者 DEVELOPMENT)

### 创建 venv 虚拟环境：

    python3 -m venv venv 

### 进入虚拟环境工作：

    source venv/bin/active


### 安装依赖包
    
    pip install -r requirements.txt

### 启动服务

    python manager.py runserver(测试)
    gunicorn -c  gunicorn.py -b 0.0.0.0:5000 wsgi:application (正式)
    
### 启动 Celery

    celery worker -A celery_worker.celery -l DEBUG (-Q default)
    celery beat -A celery_worker.celery -l DEBUG
    
### 项目结构
    .
    ├── README.md
    ├── config
    │   ├── default.py
    │   └── development.py                      配置文件
    ├── files                                   文件目录（正常文件会根据属性放 /var /tmp）
    ├── libs                                              
    │   ├── base                                基类文件
    │   │   ├── __init__.py        
    │   │   ├── model.py                        model基类
    │   │   ├── resource.py                     api的resource基类
    │   │   └── schema.py                       schema基类
    │   ├── constants.py                        常量类（枚举等）
    │   ├── error.py                            自定义error
    │   ├── redis.py                            redis
    │   └── tasks                               异步任务
    │       └── beats                           定时任务
    ├── robot                                  
    │   ├── account                             账户系统
    │   │   ├── __init__.py                     
    │   │   ├── api.py                          api文件
    │   │   ├── model.py                        db文件（db定义与CRUD）
    │   │   └── schema.py                       参数接受、校验与dump
    │   ├── __init__.py
    │   ├── api.py                              自定义api输出
    │   ├── app.py                              项目入口，初始化依赖
    │   ├── ext.py                              各种依赖入口
    │   ├── jwt.py                              jwt相关
    │   ├── sqla.py                             
    ├── manager.py                              管理文件（启动项目，管理脚本）
    ├── gunicorn.py                             uwsgi（正式服务用）
    ├── migrations                              db脚本
    ├── celery_worker.py                        异步任务
    ├── requirements.txt                        依赖文件
    └── wsgi.py
