import datetime

import arrow
import random,string

from flask_mail import Message
from ec.ext import mail, db, celery
from ec.server import User_whitelist
from ec.server.model import UserServe, Server
from ec.project.model import Project
from libs.pb.deployment import UserCreate, UserDelete, UserChange
import paramiko
import base64


@celery.task(name='security_change_cycle')
def security_change_cycle():
    from ec.server import Server,ServerSchema,Pwd_History
    servers = Server.query.filter().all()

    print('===========================================')
    print('security账户定期更新')
    for server in servers:
        print("----user-pwd change----")
        password = base64.b64encode(
            "".join(random.sample(string.ascii_letters + string.digits, 8)).encode("utf-8")).decode("utf-8")[0:12]
        print("testpwd:" + password)
        extra_vars = {
            'ansible_user': server.username,
            'ansible_password': server.password,
            # 'ansible_user': "security",
            # 'ansible_password': "security2102311TYBN0KC000310",
            'username': server.username,
            'password': password
        }
    # user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
        user_change = UserChange(hosts=[server.ip], extra_vars=extra_vars)
        res=user_change.run()
        print('执行结果：')
        print(res)
        # server.description="test"
        Pwd_History.add(server_ip=server.ip, username=server.username, old_pwd=server.password, new_pwd=password,
                        type="server_localuser", server_id=server.id)
        device =server.update(password=password)

        data = ServerSchema().dump(device).data
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
