import datetime

import arrow

from flask_mail import Message

from ec.ext import mail, db, celery
from ec.server.model import UserServe, Server
from ec.project.model import Project
from libs.pb.deployment import UserCreate, UserDelete
from ec.server import User_whitelist
from ec.requisition import RequisitionService,Requisition
from sqlalchemy import and_, or_, func

import paramiko


@celery.task(name='server_expiration_check')
def server_expiration_check():
    print('===========================================')
    print('用户检查')
    # client = paramiko.SSHClient()
    # client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # print("----del user----")
    # servers = Server.query.filter().all()
    # for server in servers:
    #     try:
    #         # 3. 连接服务器调试数据
    #         client.connect(
    #             hostname=server.ip,
    #             username=server.username,
    #             password=server.password
    #         )
    #     except Exception as e:
    #         print(e)
    #     try:
    #         stdin, stdout, stderr = client.exec_command('cat /etc/passwd|grep /bin/bash')
    #         accountlist = ["security", "root", "devops", "op", "ops","it","secteam","template"]
    #         accountlist.append(server.username)
    #
    #         for s in stdout.read().decode('utf-8').split('\n'):
    #             username = s.split(":")[0]
    #
    #             print(username)
    #             if username in accountlist:
    #                 continue
    #
    #         extra_vars = {
    #             'ansible_user': server.username,
    #             'ansible_password': server.password,
    #             # 'ansible_user': "security",
    #             # 'ansible_password': "security2102311TYBN0KC000310",
    #             'username': username,
    #         }
    #         # user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
    #         user_delete=None
    #         user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
    #         user_delete.run()
    #
    #     except Exception as e:
    #         print(e)


    now=datetime.datetime.now()
    # yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    # requisition_servers = RequisitionService.query.filter(RequisitionService.end_at > yesterday).filter(RequisitionService.end_at < now).all()
    servers = Server.query.filter().all()
    for server in servers:
        server_users_list = []
        rs_now = RequisitionService.query.filter(RequisitionService.server_id == server.id).filter(
            RequisitionService.start_at <= now).filter(RequisitionService.end_at >= now).first()
        if rs_now != None:
            requisition_id = rs_now.requisition_id
            server_users = Requisition.query.filter(Requisition.id == requisition_id).filter(
                Requisition.start_at <= now).filter(or_(Requisition.end_at >= now,
                                                        Requisition.extension_at >= now, )).first().users
            for suser in server_users:
                server_users_list.append(suser.name)
        print("server_users_list:")
        print(server_users_list)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print("----del user3----")
        try:
            # 3. 连接服务器
            client.connect(
                hostname=server.ip,
                username=server.username,
                password=server.password
            )
        except Exception as e:
            print(e)
        # try:
        stdin, stdout, stderr = client.exec_command('cat /etc/passwd|grep /bin/bash')
        local_users = User_whitelist.query.filter().all()
        accountlist = server_users_list
        for user in local_users:
            accountlist.append(user.username)

        # accountlist = ["security", "root", "devops", "op", "ops", "it", "secteam", "template","gitlab-runner"]
        accountlist.append(server.username)
        print(accountlist)
        for s in stdout.read().decode('utf-8').split('\n'):
            username = s.split(":")[0]
            print(username)
            if username in accountlist:
                continue
            print(username)
            extra_vars = {
                'ansible_user': server.username,
                'ansible_password': server.password,
                'username': username,
            }
            # user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
            user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
            user_delete.run()
        client.close()
        return None

            # deadline = datetime.datetime.now() + datetime.timedelta(days=1)
    # user_servers = UserServe.query.filter(UserServe.deadline < deadline).\
    #     filter(UserServe.send_email == 0).all()
    # data = {}
    # for user_server in user_servers:
    #     device = Server.find_by_id(user_server.device_id)
    #     if not device.program:
    #         continue
    #     user_server.send_email = 1
    #
    #     if data.get(device.program.id):
    #         data[device.program.id].append(device.ip)
    #     else:
    #         data[device.program.id] = [device.ip]
    # print(data)
    # for key, value in data.items():
    #     project = Project.find_by_id(key)
    #     recipient_emails = [user.email for user in project.users]
    #     print(recipient_emails)
    #     if not recipient_emails:
    #         continue
    #     msg = Message('机器使用截止日期提醒', recipients=recipient_emails)
    #     msg.body = '用于{}的机器{}还有一天时间到期，到期过后会自动清除服务与数据，如果要续期，请联系宋晶亮'.format(project.name, '、'.join(value))
    #     mail.send(msg)
    #
    # db.session.commit()
