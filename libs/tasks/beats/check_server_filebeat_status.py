import requests
from fabric import Connection
from ec.elklog.model import LogClient
from ec.ext import celery, db
from ec.server.model import Server

@celery.task(name='check_server_filebeat_status')
def check_server_filebeat_status():
    lc = LogClient.get_all()
    for x in lc:
        devices = Server.find_by_id(x.server_id)
        # 检测服务器是否正常连接
        try:
            # 连接服务器
            url = devices.username + "@" + devices.ip
            kw = {"password": devices.password}
            c = Connection(url, connect_kwargs=kw)
            docker_container_id = c.run(
                "echo " + devices.password + " | sudo -S docker ps | grep 'dw-filebeat' | awk '{ print $1 }'"
            )
            # 如果docker唯一ID不存在，或者run没有获取到容器id，则说明未生成filebeat镜像
            # 比对保存的和运行的容器id是否一致，不一致就重新生成容器
            if not x.docker_container_id or not docker_container_id.stdout.strip():
                # 调用接口进行生成容器
                # 修改状态
                print("不正确")
                x.push_status = 0
                LogClient.update(x)
                url = "http://127.0.0.1:5002/api/v1/log/client/operate/" + x.id
                requests.put(url)
            else:
                print("正确")
                # 存在filebeat 修改服务状态
                x.push_status = 1
            db.session.commit()
        except Exception as e:
            import traceback
            print("服务器出现问题，%s : %s" %(str(x.__dict__),str(traceback.print_exc())))
    return
