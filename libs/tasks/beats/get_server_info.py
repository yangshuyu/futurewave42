from datetime import datetime

import paramiko
from ec.ext import celery, mongodb, mail
from ec.server.model import Server
from libs.pb.deployment import DeviceInfo
from libs.redis import redis_client
from libs.tasks import device_info
from libs.tasks.send_account_checking_email import send_account_checking_email
from flask_mail import Message


@celery.task(name="get_server_info")
def get_server_info():
    servers = Server.query.filter().all()[0: 10]
    mongodb.db.server_info.drop()
    error_data = []
    for server in servers:
        print("*************************************8")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 3. 连接服务器
            client.connect(
                hostname=server.ip,
                username=server.username,
                password=server.password,
                banner_timeout=2,
                timeout=2,
                auth_timeout=2
            )
            stdin, stdout, stderr = client.exec_command("sudo ls ")
            res, err = stdout.read(), stderr.read()
            permission = '是'
            if err:
                permission = '否'
            extra_vars = {
                'ansible_user': server.username,
                'ansible_password': server.password,
            }
            ad = DeviceInfo(hosts=[server.ip], extra_vars=extra_vars)
            ad.run()
            mongodb.db.server_info.save(
                {"ip": server.ip, "_id": server.ip, "status": "succeed", "msg": "", "password": server.password,
                 "username": server.username, 'permission': permission,
                 "started_at": str(datetime.now())})
            client.close()
        except Exception as e:
            error_data.append('{} {}'.format(server.ip, str(e)))
            # send_account_checking_email(server.username, server.ip, "本地用户")
            mongodb.db.server_info.save(
                {"ip": server.ip, "_id": server.ip, "status": "error", "msg": str(e), "password": server.password,
                 "username": server.username, 'permission': '否',
                 "started_at": str(datetime.now())})

    if len(error_data) > 0:
        emails = ['810043299@qq.com']
        send_server_connection_email(emails, error_data)


def send_server_connection_email(emails, data):
    msg = Message(
        '连接问题机器反馈',
        recipients=emails
    )

    result = '<br>'.join(data)

    msg.html = '''
                                                    <html>
                                            <head>连接问题机器反馈</head>
                                            <body>
                                            <p>在 {}, 连接机器测试，有问题机器如下： <br>
                                                {}
                                            <br>
                                                请尽快修改问题
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
        result
    )
    mail.send(msg)
