import datetime

from flask_mail import Message
from sqlalchemy import func, and_

from ec.account import User
from ec.ext import db, mail, celery
from ec.requisition import Requisition, RequisitionMeta


@celery.task(name='requisition_and_server_status_synchronize')
def requisition_and_server_status_synchronize():
    now = datetime.datetime.now().replace(tzinfo=None)
    expired_requisitions = Requisition.query.filter(Requisition.status == 0). \
        filter(Requisition.end_at <= now).all()

    ## 处理过期工单
    for expired_requisition in expired_requisitions:
        expired_requisition.status = -1

        # 添加审核操作记录
        old_meta = RequisitionMeta.query.filter(
            RequisitionMeta.requisition_id == expired_requisition.id
        ).order_by(RequisitionMeta.step.desc()).limit(1).first()
        admin_user = User.query.filter(User.email == 'admin@megvii.com').first()
        RequisitionMeta.add(
            requisition_id=expired_requisition.id,
            approver=admin_user.id,
            step=old_meta.step + 1,
            type=-1,
            status=1,
            auto_commit=False,
        )
        for rs in expired_requisition.requisition_services:
            rs.deleted_at = now
        db.session.commit()

    ## 处理延期过期工单
    extension_expired_requisitions = Requisition.query.filter(Requisition.status == 2). \
        filter(Requisition.extension_status == 0).filter(Requisition.end_at <= now).all()

    ## 处理过期工单
    for extension_expired_requisition in extension_expired_requisitions:
        extension_expired_requisition.extension_status = -1

        # 添加审核操作记录
        admin_user = User.query.filter(User.email == 'admin@megvii.com').first()
        RequisitionMeta.add(
            requisition_id=extension_expired_requisition.id,
            approver=admin_user.id,
            type=-2,
            status=1,
            auto_commit=False,
        )
        db.session.commit()

    ## 处理使用结束工单
    normal_end_requisitions = Requisition.query.filter(and_(
        Requisition.status == 2,
        Requisition.extension_status.is_(None)
    )). \
        filter(Requisition.end_at <= now).all()
    extend_end_requisitions = Requisition.query.filter(Requisition.extension_status == 2). \
        filter(Requisition.extension_at <= now).all()

    end_requisitions = normal_end_requisitions + extend_end_requisitions

    for end_requisition in end_requisitions:
        end_requisition.status = 3
        end_requisition.extension_status = 3

        # 添加审核操作记录
        admin_user = User.query.filter(User.email == 'admin@megvii.com').first()
        RequisitionMeta.add(
            requisition_id=end_requisition.id,
            approver=admin_user.id,
            type=2,
            status=1,
            auto_commit=False,
        )
        db.session.commit()
        # 关闭工单。删除该工单创建的用户
        from libs.tasks.requisition_user import delete_requisition_user
        from libs.tasks.beats.white_list_cycle import init_devops_whitelist_requisition
        delete_requisition_user.apply_async(args=[end_requisition.id])
        #初始化devops超级用户
        init_devops_whitelist_requisition.apply_async(args=[end_requisition.id])


    requisition_due_reminder()

    # ## 处理时间到了工单（需要注意是否是延期工单）
    # ## 处理没有延期工单
    # timeover_requisitions = Requisition.query.filter(Requisition.status == 2). \
    #     filter(Requisition.extension_status != 2).filter(Requisition.end_at <= now).all()
    #
    # for timeover_requisition in timeover_requisitions:
    #     timeover_requisition.status = 3
    #
    #     # 添加审核操作记录
    #     old_meta = RequisitionMeta.query.filter(
    #         RequisitionMeta.requisition_id == timeover_requisition.id
    #     ).order_by(RequisitionMeta.step.desc()).limit(1).first()
    #     admin_user = User.query.filter(User.email == 'admin@megvii.com').first()
    #     meta = RequisitionMeta(
    #         requisition_id=timeover_requisition.id,
    #         approver=admin_user.id,
    #         step=old_meta.step + 1,
    #         type=2,
    #         status=1
    #     )
    #     db.session.add(meta)
    #     db.session.commit()
    #
    # ## 处理延期成功工单
    # extension_timeover_requisitions = Requisition.query.filter(Requisition.status == 2). \
    #     filter(Requisition.extension_status == 2).filter(Requisition.extension_at <= now).all()
    #
    # for extension_timeover_requisition in extension_timeover_requisitions:
    #     extension_timeover_requisition.status = 3
    #     extension_timeover_requisition.extension_status = 3
    #
    #     # 添加审核操作记录
    #     old_meta = RequisitionMeta.query.filter(
    #         RequisitionMeta.requisition_id == extension_timeover_requisitions.id
    #     ).order_by(RequisitionMeta.step.desc()).limit(1).first()
    #     admin_user = User.query.filter(User.email == 'admin@megvii.com').first()
    #     meta = RequisitionMeta(
    #         requisition_id=extension_timeover_requisition.id,
    #         approver=admin_user.id,
    #         step=old_meta.step + 1,
    #         type=2,
    #         status=1
    #     )
    #     db.session.add(meta)
    #     db.session.commit()


def requisition_due_reminder():
    ## 工单使用时间到期通知
    now = datetime.datetime.now().replace(tzinfo=None)
    email_requisitions = db.session.query(Requisition).filter(Requisition.status == 2).all()

    for email_requisition in email_requisitions:
        # 判断是否是延期工单
        if len(email_requisition.send_email) == 4:
            email_requisition.send_email = email_requisition.send_email + "0000"
            db.session.commit()


        if email_requisition.extension_status == 2:
            addtion1 = email_requisition.extension_at - email_requisition.start_at
            addtion2 = email_requisition.extension_at - now

            if addtion1.days >= 3 and addtion2.days <= 3 and \
                    email_requisition.send_email[0:1] == '0':
                send_email(3, email_requisition)
                temp = list(email_requisition.send_email)
                temp[0: 1] = '1'
                email_requisition.send_email = ''.join(temp)

            elif addtion1.days >= 2 and addtion2.days <= 2 and \
                    email_requisition.send_email[4:5] == '0':
                send_email(2, email_requisition)
                temp = list(email_requisition.send_email)
                temp[4: 5] = '1'
                email_requisition.send_email = ''.join(temp)




            elif addtion1.days >= 1 and addtion2.days <= 1 and \
                    email_requisition.send_email[1:2] == '0':
                send_email(1, email_requisition)
                temp = list(email_requisition.send_email)
                temp[1: 2] = '1'
                email_requisition.send_email = ''.join(temp)

            elif (addtion1.seconds + addtion1.days*86400) >= 10800 and (addtion2.seconds + addtion2.days*86400) <= 10800 and \
                    email_requisition.send_email[6:7] == '0':
                send_email(0.3, email_requisition)
                temp = list(email_requisition.send_email)
                temp[6: 7] = '1'
                email_requisition.send_email = ''.join(temp)

        else:
            addtion1 = email_requisition.end_at - email_requisition.start_at
            addtion2 = email_requisition.end_at - now

            if addtion1.days >= 3 and addtion2.days <= 3 and \
                    email_requisition.send_email[2:3] == '0':
                send_email(3, email_requisition)
                temp = list(email_requisition.send_email)
                temp[2: 3] = '1'
                email_requisition.send_email = ''.join(temp)

            elif addtion1.days >= 2 and addtion2.days <= 2 and \
                    email_requisition.send_email[5:6] == '0':
                send_email(2, email_requisition)
                temp = list(email_requisition.send_email)
                temp[5: 6] = '1'
                email_requisition.send_email = ''.join(temp)


            elif addtion1.days >= 1 and addtion2.days <= 1 and \
                    email_requisition.send_email[3:4] == '0':
                send_email(1, email_requisition)
                temp = list(email_requisition.send_email)
                temp[3: 4] = '1'
                email_requisition.send_email = ''.join(temp)

            elif (addtion1.seconds + addtion1.days*86400) >= 10800 and (addtion2.seconds + addtion2.days*86400) <= 10800 and \
                    email_requisition.send_email[7:8] == '0':
                send_email(0.3, email_requisition)
                temp = list(email_requisition.send_email)
                temp[7: 8] = '1'
                email_requisition.send_email = ''.join(temp)
        db.session.commit()


def send_email(day, requisition):
    msg = Message(
        "【到期提醒】您的机器工单号{}将于{}天后到期，提醒时间：{}".format(
            requisition.rid,
            day,
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ),
        recipients=[requisition.applicant_user.email]
    )
    server_msg = ""
    for rs in requisition.requisition_services:
        server_msg += "&nbsp;&nbsp;&nbsp;&nbsp;使用机器Ip:{}(所属MasterIp:{}) <br>".format(rs.server.ip, rs.master_server.ip)

    msg.html = '''

                <html>
                <head>机器工单 {} 到期提醒</head>
                <body>
                <p>您的的机器工单{}将于<p style="color: red">{}天后</p>到期，所属机器即将回收，详细信息如下：<br>
                        申请时间：<p style="color: red">{}</p> <br>
                        申请项目：<p style="color: red">{}</p>
                        到期时间：<p style="color: red">{}</p>
                        机器列表:<br>
                        {}
                        详情请去天狼效率中台查询 <a href="http://ec.cbg.megvii-inc.com/#/servers/list-requisitions">详情</a>
                </p>
                </body>
                </html>
                         '''. \
        format(
        requisition.rid,
        requisition.rid,
        day,
        requisition.created_at,
        requisition.project.name,
        requisition.end_at,
        server_msg,
    )
    mail.send(msg)


