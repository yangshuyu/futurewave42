import requests
from flask_mail import Message

from ec.ext import celery, db, mail
from libs.constants import DevOps_Cookies
from libs.pb.deployment import DevOpsDelete


@celery.task
def delete_node(node_id, need_request=True):
    from ec.node.model import Node
    from ec.server.model import Server
    node = db.session.query(Node).filter(Node.id == node_id).first()
    server = Server.find_by_id(node.server_id)
    node_extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
    }
    ad = DevOpsDelete(hosts=[server.ip], extra_vars=node_extra_vars)
    result = ad.run()
    if result == 0:
        node.delete()
    if node.type == 1 and need_request:
        master = db.session.query(Node).filter(Node.id == node.master_id).first()
        master_server = Server.find_by_id(master.server_id)
        url = "http://{}:5432/api/v1/node/{}".format(master_server.ip, master_server.hostname)
        try:
            requests.delete(url, cookies=DevOps_Cookies, timeout=2)
        except Exception as e:
            print(e)
        message = '集群{}的节点{}删除成功'.format(master_server.ip, server.ip)
    else:
        message = '集群{}删除成功'.format(server.ip)
    msg = Message('子节点删除信息', recipients=['yangshuyu@megvii.com'])
    msg.body = message
    mail.send(msg)
