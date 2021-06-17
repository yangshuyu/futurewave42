import base64
import paramiko

from sqlalchemy import and_

from ec.ext import celery, db
from libs.pb.deployment import UserCreate, UserDelete
from libs.utils.common import get_server_password


@celery.task
def add_requisition_user(requisition_id):
    from ec.requisition import Requisition, RequisitionService
    requisition = Requisition.find_by_id(requisition_id)
    requisition_servers = RequisitionService.query.filter(
        and_(
            RequisitionService.status == 1,
            RequisitionService.requisition_id == requisition_id
        )
    ).all()
    applicant_user = requisition.applicant_user

    for rs in requisition_servers:
        username = applicant_user.email.split('@')[0]
        if not username:
            return
        password = get_server_password()

        result = add_server_user(rs.server, username, password)

        if result == 0:
            rs.username = username
            rs.password = password
            requisition.user_ids=[applicant_user.id]
            db.session.commit()


@celery.task
def add_server_user_by_rs(rs_id):
    from ec.requisition import RequisitionService, Requisition
    rs = RequisitionService.find_by_id(rs_id)
    requisition = Requisition.find_by_id(rs.requisition_id)
    applicant_user = requisition.applicant_user
    username = applicant_user.email.split('@')[0]
    if not username:
        return
    password = get_server_password()
    result = add_server_user(rs.server, username, password)

    if result == 0:
        rs.username = username
        rs.password = password
        requisition.user_ids = [applicant_user.id]
        db.session.commit()


@celery.task
def delete_requisition_user(requisition_id):
    from ec.requisition import RequisitionService
    from ec.server import User_whitelist
    print("------删除本地用户------")
    requisition_servers = RequisitionService.query.filter(
        and_(
            RequisitionService.status == 1,
            RequisitionService.requisition_id == requisition_id
        )
    ).all()
    for rs in requisition_servers:
        # if not rs.username:
            # continue
        server = rs.server
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
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
        local_users=User_whitelist.query.filter().all()
        accountlist=[]
        for user in local_users:
            accountlist.append(user.username)
        accountlist.append(server.username)
        for s in stdout.read().decode('utf-8').split('\n'):
            username = s.split(":")[0]
            print(username)
            if username in accountlist:
                continue
            print(username)
            delete_server_user(server, username)


@celery.task
def delete_server_user_by_rs(rs_id):
    from ec.requisition import RequisitionService, Requisition
    rs = RequisitionService.find_by_id(rs_id)
    requisition = Requisition.find_by_id(rs.requisition_id)
    applicant_user = requisition.applicant_user
    username = applicant_user.email.split('@')[0]
    if not username:
        return

    delete_server_user(rs.server, username)


def add_server_user(server, username, password):

    extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
        'username': username,
        'password': password
    }
    user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
    user_delete.run()
    user_create = UserCreate(hosts=[server.ip], extra_vars=extra_vars)
    result = user_create.run()
    return result


def delete_server_user(server, username):
    extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
        # 'ansible_user': "security",
        # 'ansible_password': "security2102311TYBN0KC000310",
        'username': username,
    }
    # user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
    user_delete = UserDelete(hosts=[server.ip], extra_vars=extra_vars)
    user_delete.run()
