import datetime

from flask_mail import Message

from ec.ext import celery, mail


@celery.task
def send_account_checking_email(account,server_ip,type):
    from ec.account.model import User
    users = User.get_users_by_role(1)
    # users =User.get_users_by_query(q="songjingliang")
    emails = [user.email for user in users]
    emails=["songjingliang@megvii.com"]
    send_application_email(emails, account,server_ip,type)


def send_application_email(emails,  account,server_ip,type):
    msg = Message(
        '账号异常提醒',
        recipients=emails
    )

    msg.html = '''
                                                    <html>
                                            <head>账号异常提醒</head>
                                            <body>
                                            <p>服务器{} 账号巡检出现异常，异常账号：{}，类型：{}
                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/list-servers">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        server_ip,
        account,
        type
    )
    mail.send(msg)


