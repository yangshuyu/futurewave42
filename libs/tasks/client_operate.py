import os
from ec.ext import celery
from fabric import *
import patchwork.transfers


@celery.task
def operate_client(client_id, filebeat_version):
    print(client_id, filebeat_version)
    constant_vars = {
        "base_path": "ec_log_client",
        "filebeat_file_path": os.getcwd() + "/libs/filebeat_log/" + filebeat_version,
    }
    print(constant_vars)
    from ec.elklog.model import LogClient

    lc = LogClient.find_by_id(client_id)
    # push_status: 0:关闭，1：开启，2：关闭中，3：开启中
    old_push_status = lc.push_status
    if str(old_push_status) == "3":
        open_client(lc, constant_vars)
    elif str(old_push_status) == "2":
        close_client(lc)
    elif str(old_push_status) == "0" or str(old_push_status) == "1":
        print("status状态不正确，无法启动或者关闭！")


def close_client(lc):
    docker_container_id = lc.docker_container_id
    url = lc.server.username + "@" + lc.server.ip
    kw = {"password": lc.server.password}
    print(url, kw)
    c = Connection(url, connect_kwargs=kw)
    stop_cmd = "echo " + lc.server.password + " | sudo -S docker stop " + docker_container_id
    rm_cmd = "echo " + lc.server.password + " | sudo -S docker rm " + docker_container_id
    stop_resp = c.run(stop_cmd)
    if stop_resp.return_code == 0:
        rm_resp = c.run(rm_cmd)
        if rm_resp.return_code == 0:
            # args = {"push_status": 0, "docker_container_id": "", "client_desc": "停止成功"}
            args = {"push_status": 0, "docker_container_id": ""}
            lc.update(**args)
    else:
        # args = {"push_status": 2, "client_desc": "停止失败，请检查！"}
        args = {"push_status": 2}
        lc.update(**args)


def open_client(lc, constant_vars):
    print(lc.server.ip, lc.server.username, lc.server.password)
    url = lc.server.username + "@" + lc.server.ip
    kw = {"password": lc.server.password}
    print(url, kw)
    c = Connection(url, connect_kwargs=kw)
    if c.run("test -d {}".format(constant_vars["base_path"]), warn=True).failed:
        # Folder doesn't exist
        c.run("mkdir -p {}".format(constant_vars["base_path"]))
        print("目录不存在，创建目录成功！")
    else:
        print("目录已存在！")
    try:
        with c.cd(constant_vars["base_path"]):
            for parent, dirnames, filenames in os.walk(
                constant_vars["filebeat_file_path"], followlinks=True
            ):
                for filename in filenames:
                    file_path = os.path.join(parent, filename)
                    c.put(file_path, constant_vars["base_path"])
                    print("上传 %s 成功" % filename)
                    if filename == "start.sh":
                        c.run("sed -i 's/\r//' start.sh")
                        c.run("chmod +x start.sh")
                    elif filename == "down_compose_python.sh":
                        c.run("chmod +x down_compose_python.sh")
            c.run("echo " + lc.server.password + " | sudo -S sh start.sh")
            docker_container_id = c.run(
                "echo " + lc.server.password + " | sudo -S docker ps | grep 'dw-filebeat' | awk '{ print $1 }'"
            )
            print(
                docker_container_id.return_code,
                docker_container_id.stdout,
                len(docker_container_id.stdout.strip()),
            )
            if (
                docker_container_id.return_code == 0
                and len(docker_container_id.stdout.strip()) == 12
            ):
                # args = {
                #     "push_status": 1,
                #     "docker_container_id": str(docker_container_id.stdout),
                #     "client_desc": "启动成功",
                # }
                args = {
                    "push_status": 1,
                    "docker_container_id": str(docker_container_id.stdout)
                }
                lc.update(**args)
            else:
                print("启动失败，未获取到容器ID")
                # args = {"push_status": 0, "client_desc": "启动失败！"}
                args = {"push_status": 0}
                lc.update(**args)
    except Exception as e:
        print(str(e))
        # args = {"push_status": 0, "client_desc": "sudo执行失败，启动失败！"}
        args = {"push_status": 0}
        lc.update(**args)
