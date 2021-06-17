import requests
from flask_mail import Message

from ec.ext import celery, db, mail
from libs.constants import DevOps_Cookies
from libs.pb.deployment import DevOpsManagerCreator, DevOpsAgentsCreator


@celery.task
def create_master(master_id):
    from ec.node.model import Node
    from ec.server.model import Server
    master = Node.find_by_id(master_id)
    master_server = Server.find_by_id(master.server_id)
    nodes = master.nodes

    master_extra_vars = {
        'ansible_user': master_server.username,
        'ansible_password': master_server.password,
        'manager_deb_version': '20.8.1',
        "ansible_sudo_pass": master_server.password,
        "manager_host": master_server.ip
    }
    mc = DevOpsManagerCreator(hosts=[master_server.ip], extra_vars=master_extra_vars)
    mc_result = mc.run()
    print(mc_result)
    if mc_result != 0:
        master.status = 2
    else:
        master.status = 1

    for node in nodes:
        # node = create_node(node.id)
        node_server = Server.find_by_id(node.server_id)
        node_extra_vars = {
            'ansible_user': node_server.username,
            'ansible_password': node_server.password,
            'manager_deb_version': '20.8.1',
            "ansible_sudo_pass": node_server.password,
            "manager_host": master_server.ip
        }
        nc = DevOpsAgentsCreator(hosts=[node_server.ip], extra_vars=node_extra_vars)
        nc_result = nc.run()
        if nc_result != 0:
            node.status = 2
        else:
            node.status = 1
        print(node, nc_result)
    db.session.commit()

    if master.status == 2:
        message = '集群{}部署失败'.format(master_server.ip)
    else:
        failure_node_servers = []
        for node in nodes:
            if node.status == 2:
                node_server = Server.find_by_id(node.server_id)
                failure_node_servers.append(node_server.ip)
        if len(failure_node_servers) > 0:
            message = '集群{}的节点{}部署失败'.format(master_server.ip, '、'.join(failure_node_servers))
        else:
            message = '集群{}部署成功'.format(master_server.ip)

        # 设置加密狗
        try:
            url = 'http://{}:5432/api/v1/cmu/ip'.format(master_server.ip)
            payload = {
                'ip': '10.201.102.80'
            }
            res = requests.post(url, data=payload, cookies=DevOps_Cookies, timeout=60)
            print(res.content)
        except Exception as e:
            print('set dog error')
            print(e)

        # 设置数据包加密地址
        try:
            url = 'http://{}:5432/api/v1/cluster/hostip'.format(master_server.ip)
            payload = {
                'dpkgServerAddr': '10.201.102.121',
                'hostip': master_server.ip,
                'sshClientPort': '2222',
                'eventRetentionTime': '7776000'
            }
            res = requests.put(url, data=payload, cookies=DevOps_Cookies, timeout=10)
            print(res.content)
        except Exception as e:
            print('set data error')
            print(e)


    #设置集群管理节点
    manager_node = None
    for node in nodes:
        if node.server and not node.server.graphic_cards:
            manager_node = node

    if manager_node:
        try:
            url = 'http://{}:5432/api/v1/node/{}'.\
                format(manager_node.server.ip, manager_node.server.hostname)
            payload = {
                'tags': 'manager_node',
            }
            res = requests.put(url, data=payload, cookies=DevOps_Cookies, timeout=10)
            print(res.content)
        except Exception as e:
            print('set data error')
            print(e)

    project = master.project
    users = []
    if project:
        users = project.users
    if len(users) > 0:
        msg = Message('机器', recipients=[user.email for user in users])
        msg.body = message
        mail.send(msg)


@celery.task
def create_node(node_id):
    from ec.node.model import Node
    from ec.server.model import Server
    node = Node.find_by_id(node_id)
    node_server = Server.find_by_id(node.server_id)
    node_extra_vars = {
        'ansible_user': node_server.username,
        'ansible_password': node_server.password,
        'manager_deb_version': '20.8.1',
        "manager_host": node_server.ip
    }
    nc = DevOpsAgentsCreator(hosts=[node_server.ip], extra_vars=node_extra_vars)
    nc_result = nc.run()
    if nc_result != 0:
        node.status = 2
    else:
        node.status = 1

    return node
