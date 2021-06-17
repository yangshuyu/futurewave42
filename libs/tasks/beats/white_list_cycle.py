import datetime

import arrow,time
import random,string,requests

from flask_mail import Message
from ec.ext import mail, db, celery
from ec.server.model import UserServe, Server
from ec.project.model import Project
from libs.pb.deployment import UserCreate, UserDelete, UserChange
import paramiko
import base64
from libs.tasks.send_account_checking_email import send_account_checking_email


@celery.task(name='white_list_cycle')
def white_list_cycle():
    from ec.server import Server,ServerSchema,Pwd_History
    from ec.requisition.model import Requisition,RequisitionService
    from ec.department_opti.model import EcStaff
    from sqlalchemy import and_, or_, func
    servers = Server.query.filter().all()

    print('===========================================')
    print('devops超级用户及白名单检查')
    password1 = base64.b64encode(
        "".join(random.sample(string.ascii_letters + string.digits, 8)).encode("utf-8")).decode("utf-8")[0:12]
    print("testpwd1111:" + password1)
    # 获取天狼白名单
    ec_devops_whitelist=EcStaff.query.filter(and_(EcStaff.devops_whitelist, EcStaff.empStatus == "Norm")).all()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for server in servers:
        # 获取服务器当前工单用户
        # users = User.find_by_ids(user_ids)
        #调试数据
        # now='2020-09-10 00:00:00'
        server_users_list=[]
        rs=RequisitionService.query.filter(RequisitionService.server_id==server.id).filter(
            RequisitionService.start_at <= now).filter(RequisitionService.end_at >= now).first()
        if rs !=None:
            requisition_id=rs.requisition_id
            server_users = Requisition.query.filter(Requisition.id == requisition_id).filter(
                Requisition.start_at <= now).filter(or_(Requisition.end_at >= now,
                                                                             Requisition.extension_at >= now, )).first().users
            for suser in server_users:
                server_users_list.append(suser.name)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("----devops_whitelist_check----")
        #调试数据
        # server.ip="10.122.100.225"
        # server.username="security"
        # server.password="securityKSSMS3000H21905150014"
        try:
            # 3. 连接服务器
            client.connect(
                hostname=server.ip,
                username=server.username,
                password=server.password
            )
        except Exception as e:
            print(e)
        is_devops_master = 0
        try:
            stdin, stdout, stderr = client.exec_command('supervisorctl status|grep devops-manager-core:devops-manager')

            if "devops-manager-core:devops-manager" in stdout.read().decode('utf-8'):
                is_devops_master = 1
        except Exception as e:
            print(e)
        if is_devops_master ==1:
            #如果没有密码则更改初始化密码
            if server.devops_pwd==None or server.devops_pwd=="-":
                try:
                    stdin, stdout, stderr = client.exec_command('sudo devops-manager -superuser -passwd', get_pty=True)
                    stdin.write('%s\n' % password1)
                    time.sleep(1)
                    stdin.write('%s\n' % password1)
                    time.sleep(1)
                    stdin.flush()
                    s = stdout.read().decode('utf-8')
                    #修改成功
                    if "successfully"in s:
                        Server.add_devops_pwd(id=server.id,pwd=password1)
                        Pwd_History.add(server_ip=server.ip, username="nimda-spoved", old_pwd=server.devops_pwd,
                                        new_pwd=password1, type="devops_admin", server_id=server.id)
                except Exception as e:
                    print(e)

            url = "http://"+server.ip+":5432/api/v1/user/login"
            params = {"username": "nimda-spoved", "password": server.devops_pwd}
            res = requests.post(url, params=params)
            data = res.json()
            if data.get("Status")!=True:
            #登录失败，发送邮件检查账号密码
                send_account_checking_email("nimda-spoved",server.ip,"devops-admin")
            else:
                #检查白名单
                DevOps_Cookies = {
                    'devops-login': res.cookies._cookies[server.ip]["/"]["devops-login"].value
                }
                #打开白名单
                permitted_user_switch_res = requests.post("http://"+server.ip+":5432/api/v1/permitted_user_switch",
                                          cookies=DevOps_Cookies).json()
                #获取devops的白名单
                devops_whitelist_users = requests.get("http://"+server.ip+":5432/api/v1/permitted_user",
                              cookies=DevOps_Cookies).json()["users"]

                devops_whitelist=[]
                for i in devops_whitelist_users:
                    devops_whitelist.append(i["name"])

                for whitelist_user in ec_devops_whitelist:
                    #没有则创建
                    if whitelist_user.staff_name_2  not in devops_whitelist:
                        requests.post("http://"+server.ip+":5432/api/v1/permitted_user",
                                                  params={"name": whitelist_user.staff_name_2}, cookies=DevOps_Cookies).json()
                    else:
                        devops_whitelist.remove(whitelist_user.staff_name_2)
                for whitelist_user in server_users_list:
                    if whitelist_user not in devops_whitelist:
                        requests.post("http://" + server.ip + ":5432/api/v1/permitted_user",
                                      params={"name": whitelist_user},
                                      cookies=DevOps_Cookies).json()
                    else:
                        devops_whitelist.remove(whitelist_user)

                #多余白名单删除
                for u in devops_whitelist:
                    requests.delete("http://" + server.ip + ":5432/api/v1/permitted_user/"+u,
                                   cookies=DevOps_Cookies).json()
        client.close()
        return None


def update_white_list():
    from ec.server import Server,ServerSchema,Pwd_History
    from ec.requisition.model import Requisition,RequisitionService
    from ec.department_opti.model import EcStaff
    from sqlalchemy import and_, or_, func
    servers = Server.query.filter(Server.devops_pwd!=None).all()

    print('===========================================')
    print('更新白名单')
    password1 = base64.b64encode(
        "".join(random.sample(string.ascii_letters + string.digits, 8)).encode("utf-8")).decode("utf-8")[0:12]
    print("testpwd1111:" + password1)
    # 获取天狼白名单
    ec_devops_whitelist=EcStaff.query.filter(and_(EcStaff.devops_whitelist, EcStaff.empStatus == "Norm")).all()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for server in servers:
        # 获取服务器当前工单用户
        # users = User.find_by_ids(user_ids)
        #调试数据
        # now='2020-09-10 00:00:00'
        server_users_list=[]
        rs=RequisitionService.query.filter(RequisitionService.server_id==server.id).filter(
            RequisitionService.start_at <= now).filter(RequisitionService.end_at >= now).first()
        if rs !=None:
            requisition_id=rs.requisition_id
            server_users = Requisition.query.filter(Requisition.id == requisition_id).filter(
                Requisition.start_at <= now).filter(or_(Requisition.end_at >= now,
                                                                             Requisition.extension_at >= now, )).first().users
            for suser in server_users:
                server_users_list.append(suser.name)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("----devops_whitelist_check----")
        #调试数据
        # server.ip="10.122.100.225"
        # server.username="security"
        # server.password="securityKSSMS3000H21905150014"
        try:
            # 3. 连接服务器
            client.connect(
                hostname=server.ip,
                username=server.username,
                password=server.password
            )
        except Exception as e:
            print(e)
        is_devops_master = 0
        try:
            stdin, stdout, stderr = client.exec_command('sudo supervisorctl status|grep devops-manager-core:devops-manager')
            out=stdout.read().decode('utf-8')
            if "devops-manager-core:devops-manager" in out:
                is_devops_master = 1
        except Exception as e:
            print(e)
        if is_devops_master ==1:
            #如果没有密码则更改初始化密码
            if server.devops_pwd==None or server.devops_pwd=="-":
                try:
                    stdin, stdout, stderr = client.exec_command('sudo devops-manager -superuser -passwd', get_pty=True)
                    stdin.write('%s\n' % password1)
                    time.sleep(1)
                    stdin.write('%s\n' % password1)
                    time.sleep(1)
                    stdin.flush()
                    s = stdout.read().decode('utf-8')
                    #修改成功
                    if "successfully"in s:
                        Server.add_devops_pwd(id=server.id,pwd=password1)
                        Pwd_History.add(server_ip=server.ip, username="nimda-spoved", old_pwd=server.devops_pwd,
                                        new_pwd=password1, type="devops_admin", server_id=server.id)
                except Exception as e:
                    print(e)
            url = "http://"+server.ip+":5432/api/v1/user/login"
            params = {"username": "nimda-spoved", "password": server.devops_pwd}
            res = requests.post(url, params=params)
            data = res.json()
            if data.get("Status")!=True:
            #登录失败，发送邮件检查账号密码
                send_account_checking_email("nimda-spoved",server.ip,"devops-admin")
            else:
                #检查白名单
                DevOps_Cookies = {
                    'devops-login': res.cookies._cookies[server.ip]["/"]["devops-login"].value
                }
                #打开白名单
                permitted_user_switch_res = requests.post("http://"+server.ip+":5432/api/v1/permitted_user_switch",
                                          cookies=DevOps_Cookies).json()
                #获取devops的白名单
                devops_whitelist_users = requests.get("http://"+server.ip+":5432/api/v1/permitted_user",
                              cookies=DevOps_Cookies).json()["users"]

                devops_whitelist=[]
                for i in devops_whitelist_users:
                    devops_whitelist.append(i["name"])

                for whitelist_user in ec_devops_whitelist:
                    #没有则创建
                    if whitelist_user.staff_name_2  not in devops_whitelist:
                        requests.post("http://"+server.ip+":5432/api/v1/permitted_user",
                                                  params={"name": whitelist_user.staff_name_2}, cookies=DevOps_Cookies).json()
                    else:
                        devops_whitelist.remove(whitelist_user.staff_name_2)
                for whitelist_user in server_users_list:
                    if whitelist_user not in devops_whitelist:
                        requests.post("http://" + server.ip + ":5432/api/v1/permitted_user",
                                      params={"name": whitelist_user},
                                      cookies=DevOps_Cookies).json()
                    else:
                        devops_whitelist.remove(whitelist_user)

                #多余白名单删除
                for u in devops_whitelist:
                    requests.delete("http://" + server.ip + ":5432/api/v1/permitted_user/"+u,
                                   cookies=DevOps_Cookies).json()
        client.close()
        return None


@celery.task
def init_devops_whitelist_requisition(requisition_id):
    from ec.department_opti.model import EcStaff
    from sqlalchemy import and_, or_, func
    from ec.requisition.model import Requisition,RequisitionService
    from ec.server import Server, ServerSchema, Pwd_History
    from ec.requisition.model import RequisitionService
    requisition_servers=RequisitionService.query.filter(RequisitionService.requisition_id==requisition_id).all()
    for requisition_server in requisition_servers:
        server=requisition_server.server
        print("server_ip:")
        print(server.ip)
        #调试数据
        # server.ip="10.122.100.225"
        # server.username="security"
        # server.password="securityKSSMS3000H21905150014"
        password1 = base64.b64encode(
            "".join(random.sample(string.ascii_letters + string.digits, 8)).encode("utf-8")).decode("utf-8")[0:12]
        print("testpwd1111:" + password1)
        # 获取天狼白名单
        ec_devops_whitelist = EcStaff.query.filter(and_(EcStaff.devops_whitelist, EcStaff.empStatus == "Norm")).all()
        # 获取服务器当前工单用户
        # users = User.find_by_ids(user_ids)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        server_users_list=[]
        rs=RequisitionService.query.filter(RequisitionService.server_id==server.id).filter(
            RequisitionService.start_at <= now).filter(RequisitionService.end_at >= now).first()
        if rs !=None:
            requisition_id=rs.requisition_id
            server_users = Requisition.query.filter(Requisition.id == requisition_id).filter(
                Requisition.start_at <= now).filter(or_(Requisition.end_at >= now,
                                                                             Requisition.extension_at >= now, )).first().users
            for suser in server_users:
                server_users_list.append(suser.name)
        # users = User.find_by_ids(user_ids)
        # Requisition.query.join(RequisitionService, RequisitionService.requisition_id == Requisition.id). \
        #             filter(RequisitionService.server_id == self.id).filter()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("----init_devops_whitelist----")
        try:
            # 3. 连接服务器
            client.connect(
                hostname=server.ip,
                username=server.username,
                password=server.password
            )
        except Exception as e:
            print(e)
        is_devops_master = 0
        try:
            stdin, stdout, stderr = client.exec_command(
                'sudo supervisorctl status|grep devops-manager-core:devops-manager')
            # aa=stdout.read().decode('utf-8')
            if "devops-manager-core:devops-manager" in stdout.read().decode('utf-8'):
                is_devops_master = 1
        except Exception as e:
            print(e)
        if is_devops_master == 1:
            # 如果没有密码则更改初始化密码
            a=server.devops_pwd
            if server.devops_pwd == None:
                server.devops_pwd="-"
            try:
                stdin, stdout, stderr = client.exec_command('sudo devops-manager -superuser -passwd', get_pty=True)
                stdin.write('%s\n' % password1)
                time.sleep(1)
                stdin.write('%s\n' % password1)
                time.sleep(1)
                stdin.flush()
                s =stdout.read().decode('utf-8')
                print(s)
                if "successfully" in s:
                    Pwd_History.add(server_ip=server.ip, username="nimda-spoved", old_pwd=server.devops_pwd,
                                    new_pwd=password1, type="devops_admin", server_id=server.id)
                    Server.add_devops_pwd(id=server.id, pwd=password1)
            except Exception as e:
                print(e)
            url = "http://" + server.ip + ":5432/api/v1/user/login"
            params = {"username": "nimda-spoved", "password": password1}
            res = requests.post(url, params=params)
            data = res.json()
            if data["Status"] != True:
                # 密码不对
                a = 1
            else:
                # 检查白名单
                DevOps_Cookies = {
                    'devops-login': res.cookies._cookies[server.ip]["/"]["devops-login"].value
                }
                # 打开白名单
                permitted_user_switch_res = requests.post(
                    "http://" + server.ip + ":5432/api/v1/permitted_user_switch",
                    cookies=DevOps_Cookies).json()
                # 获取devops的白名单
                devops_whitelist_users = requests.get("http://" + server.ip + ":5432/api/v1/permitted_user",
                                                      cookies=DevOps_Cookies).json()["users"]

                devops_whitelist = []
                for i in devops_whitelist_users:
                    devops_whitelist.append(i["name"])

                for whitelist_user in ec_devops_whitelist:
                    # 没有则创建
                    if whitelist_user.staff_name_2 not in devops_whitelist:
                        requests.post("http://" + server.ip + ":5432/api/v1/permitted_user",
                                      params={"name": whitelist_user.staff_name_2},
                                      cookies=DevOps_Cookies).json()
                    else:
                        devops_whitelist.remove(whitelist_user.staff_name_2)
                for whitelist_user in server_users_list:
                    if whitelist_user not in devops_whitelist:
                        requests.post("http://" + server.ip + ":5432/api/v1/permitted_user",
                                      params={"name": whitelist_user},
                                      cookies=DevOps_Cookies).json()
                    else:
                        devops_whitelist.remove(whitelist_user)
                # 多余白名单删除
                for u in devops_whitelist:
                    requests.delete("http://" + server.ip + ":5432/api/v1/permitted_user/" + u,
                                    cookies=DevOps_Cookies).json()
        client.close()

    return None


