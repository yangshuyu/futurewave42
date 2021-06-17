import datetime

from flask_mail import Message

from ec.ext import celery, mail


@celery.task
def send_requisition_email(meta_id):
    from ec.requisition.model import Requisition, RequisitionMeta
    requisition_meta = RequisitionMeta.find_by_id(meta_id)
    requisition = Requisition.find_by_id(requisition_meta.requisition_id)

    if requisition_meta.type == 0:
        approver_users = requisition.approver_users
        emails = [approver_user.email for approver_user in approver_users]
        # emails = ['810043299@qq.com']
        send_application_email(emails, requisition)

    if requisition_meta.type == 1 and requisition_meta.status == 0:
        applicant_user = requisition.applicant_user
        emails = [applicant_user.email]
        # emails = ['810043299@qq.com']
        send_verify_failure_email(emails, requisition)

    if requisition_meta.type == 1 and requisition_meta.status == 1:
        applicant_user = requisition.applicant_user
        emails = [applicant_user.email]
        # emails = ['810043299@qq.com']
        send_verify_success_email(emails, requisition)

    if requisition_meta.type == 3:
        approver_users = requisition.approver_users
        emails = [approver_user.email for approver_user in approver_users]
        # emails = ['810043299@qq.com']
        send_extend_email(emails, requisition)

    if requisition_meta.type == 4 and requisition_meta.status == 0:
        applicant_user = requisition.applicant_user
        emails = [applicant_user.email]
        # emails = ['810043299@qq.com']
        send_extend_verify_failure_email(emails, requisition)

    if requisition_meta.type == 4 and requisition_meta.status == 1:
        applicant_user = requisition.applicant_user
        emails = [applicant_user.email]
        # emails = ['810043299@qq.com']
        send_extend_verify_success_email(emails, requisition)


def send_application_email(emails, requisition):
    msg = Message(
        '新机器工单提醒',
        recipients=emails
    )

    msg.html = '''
                                                    <html>
                                            <head>新机器工单提醒</head>
                                            <body>
                                            <p>在 {}，有新提交的工单，编号：{}，项目：{}，版本：{}，需要您进行审批，请及时查看 <br>

                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/requisitions-approve">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        datetime.datetime.strftime(requisition.created_at, '%Y-%m-%d %H:%M:%S'),
        requisition.rid,
        requisition.project.description,
        requisition.project.name,
    )
    mail.send(msg)


def send_verify_success_email(emails, requisition):
    msg = Message(
        '审核成功提醒',
        recipients=emails
    )

    msg.html = '''
                                                    <html>
                                            <head>机器审批成功提醒</head>
                                            <body>
                                            <p>您在 {} 提交的工单，编号：{}，项目：{}，版本：{}，已经由管理员进行了审批，并分配了机器如下： <br>
                                            {}

                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/requisitions-approve">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        datetime.datetime.strftime(requisition.created_at, '%Y-%m-%d %H:%M:%S'),
        requisition.rid,
        requisition.project.description,
        requisition.project.name,
        "<br>".join([x.server.ip for x in requisition.requisition_services])
    )
    mail.send(msg)


def send_verify_failure_email(emails, requisition):
    msg = Message(
        '审核失败提醒',
        recipients=emails
    )

    msg.html = '''
                                                    <html>
                                            <head>工单审核失败提醒</head>
                                            <body>
                                            <p>您在 {} 提交的工单，编号：{}，项目：{}，版本：{}，已经由管理员进行了审批，审批失败。 <br>

                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/requisitions-approve">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        datetime.datetime.strftime(requisition.created_at, '%Y-%m-%d %H:%M:%S'),
        requisition.rid,
        requisition.project.description,
        requisition.project.name,
    )
    mail.send(msg)


def send_extend_email(emails, requisition):
    msg = Message(
        '延期工单提醒',
        recipients=emails
    )
    msg.html = '''
                                                    <html>
                                            <head>新延期工单提醒</head>
                                            <body>
                                            <p>在 {} 有新提交的延期工单，编号：{}，项目：{}，版本：{}，需要您进行审批，请及时查看： <br>

                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/requisitions-approve">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'),
        requisition.rid,
        requisition.project.description,
        requisition.project.name,
    )
    mail.send(msg)


def send_extend_verify_success_email(emails, requisition):
    msg = Message(
        '延期工单审核成功提醒',
        recipients=emails
    )

    msg.html = '''
                                                    <html>
                                            <head>延期工单审核成功提醒</head>
                                            <body>
                                            <p>您提交的延期工单，编号：{}，项目：{}，版本：{}，已经由管理员进行了审批，并分配了机器如下： <br>
                                            {}

                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/requisitions-approve">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        requisition.rid,
        requisition.project.description,
        requisition.project.name,
        "<br>".join([x.server.ip for x in requisition.requisition_services])
    )
    mail.send(msg)


def send_extend_verify_failure_email(emails, requisition):
    msg = Message(
        '延期工单审核失败提醒',
        recipients=emails
    )
    msg.html = '''
                                                    <html>
                                            <head>延期工单审核失败提醒</head>
                                            <body>
                                            <p>您提交的延期工单，编号：{}，项目：{}，版本：{}，已经由管理员进行了审批，延期失败 <br>

                                            <br>
                                                请尽快去天狼中台查看 <a href="http://ec.cbg.megvii-inc.com/#/servers/requisitions-approve">详情</a>
                                            </p>

                                            </body>
                                            </html>
                                                '''.format(
        requisition.rid,
        requisition.project.description,
        requisition.project.name,
    )
    mail.send(msg)
