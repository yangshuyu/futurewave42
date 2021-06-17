import datetime
import uuid

from sqlalchemy import and_

from ec.ext import celery, db
from ec.galaxy_tool.model import GalaxyClearServerDataRecord
from ec.node.model import Node
from libs.pb.deployment import ServicesStop, DataDelete, ServicesDeploy
from libs.tasks.execute_pipeline import clear_runonce

@celery.task
def execute_clear_server_data(**kwargs):
    server_id = kwargs.get("server_id")
    user_id = kwargs.get("user_id")

    id = str(uuid.uuid4())
    gcsdr = GalaxyClearServerDataRecord(
        id=id,
        user_id=user_id,
        msg=[{"time": str(datetime.datetime.now())[:19], "msg":"清理中..."}],
        server_id=server_id,
        status="进行中"
    )
    db.session.add(gcsdr)
    db.session.commit()

    kwargs["record_id"] = id
    try:
        res ,status= start(**kwargs)
    except Exception as e:
        res  = [ {"time": str(datetime.datetime.now())[:19], "msg": "【异常】 ：{} ".format(str(e))}  ]
        status = False

    gcsdr = GalaxyClearServerDataRecord.find_by_id(id)
    gcsdr.msg = res
    gcsdr.status = "完成" if status else "失败"
    db.session.add(gcsdr)
    db.session.commit()

def start(**kwargs):
    server_id = kwargs.get("server_id")
    record_id = kwargs.get("record_id")
    node_obj = Node.query.filter(and_(
        Node.server_id == server_id ,Node.deleted_at == None)).first()
    if node_obj.type == 0:
        master_obj = node_obj
        node_objs = Node.query.filter(Node.master_id == node_obj.id, Node.deleted_at == None).all()
    else:
        master_obj = Node.find_by_id(node_obj.master_id)
        node_objs = Node.query.filter(Node.master_id == node_obj.master_id, Node.deleted_at == None).all()

    msg = []
    status = False
    extra_vars = {
        'ansible_user': master_obj.server.username,
        'ansible_password': master_obj.server.password,
        'manager_host': master_obj.server.ip,
        "kind": 1,
        "timeout": 300,
        "services": ""
    }

    services_stop = ServicesStop(hosts=[master_obj.server.ip], extra_vars=extra_vars)
    result = services_stop.run()
    if result == 0:
        msg.append({"time": str(datetime.datetime.now())[:19], "msg": "【停止服务】：Master{ip} 停止成功".format(ip=master_obj.server.ip)})
    else:
        msg.append({"time": str(datetime.datetime.now())[:19], "msg": "【停止服务】：Master{ip} 停止失败".format(ip=master_obj.server.ip)})
        return msg ,status

    gcsdr = GalaxyClearServerDataRecord.find_by_id(record_id)
    gcsdr.msg = msg
    db.session.add(gcsdr)
    db.session.commit()

    dir = [
        r'`ls /mnt/data/ |grep -v "megvii\b"|grep -v "megvii-devops\b" |grep -v "lost+found\b" `',
        "/mnt/data-important/*"
           ]
    for node in node_objs:
        if node and node.server:
            extra_vars = {
                'ansible_user': node.server.username,
                'ansible_password': node.server.password,
                'manager_host': node.server.ip,
                'timeout': 1200,
                "dirs": dir
            }
            node_data_delete = DataDelete(hosts=[node.server.ip], extra_vars=extra_vars)
            node_result = node_data_delete.run()
            if node_result == 0:
                msg.append({"time": str(datetime.datetime.now())[:19], "msg":
                    "【删除数据】：删除Node{ip}目录 成功 - {dir}".format(ip=node.server.ip,
                                                            dir=" , ".join(dir))})
            else:
                msg.append({"time": str(datetime.datetime.now())[:19], "msg":
                    "【删除数据】：删除Node{ip}目录 失败 - {dir}".format(ip=node.server.ip,
                                                            dir=" , ".join(dir))})
                return msg,status
    gcsdr = GalaxyClearServerDataRecord.find_by_id(record_id)
    gcsdr.msg = msg
    db.session.add(gcsdr)
    db.session.commit()
    try:
        clear_runonce(server=master_obj.server)
        msg.append({"time": str(datetime.datetime.now())[:19],
                    "msg": "【清理RunOnce】：Master{ip} 成功".format(ip=master_obj.server.ip)})
    except Exception as e:
        msg.append({"time": str(datetime.datetime.now())[:19],
                    "msg": "【清理RunOnce】：Master{ip} 失败 - {e}".format(ip=master_obj.server.ip ,e=str(e))})
        return msg ,status

    gcsdr = GalaxyClearServerDataRecord.find_by_id(record_id)
    gcsdr.msg = msg
    db.session.add(gcsdr)
    db.session.commit()

    all_services = [
        'gpdb', 'core', 'galaxy', 'vsr', 'shenbu', 'iot',
        'cloud_bridge', 'megcity', 'insight', 'wisdom', 'kunlun',
        'viid', 'edge_server', 'mpsa', 'covid', 'wormhole', 'mpsa', 'gsp', 'gmp'
    ]

    services = ','.join(all_services)
    extra_vars = {
        'ansible_user': master_obj.server.username,
        'ansible_password': master_obj.server.password,
        'manager_host': master_obj.server.ip,
        "kind": 2,
        "services": services,
        "timeout": 2000
    }

    services_deploy = ServicesDeploy(hosts=[master_obj.server.ip], extra_vars=extra_vars)
    result = services_deploy.run()
    if result == 0:
        msg.append({"time": str(datetime.datetime.now())[:19],
                    "msg": "【部署服务】：Master{ip} 成功".format(ip=master_obj.server.ip)})
    else:
        msg.append({"time": str(datetime.datetime.now())[:19],
                    "msg": "【部署服务】：Master{ip} 失败".format(ip=master_obj.server.ip)})
    return msg , True