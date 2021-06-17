from requests import request

from ec.ext import celery
from ec.server.model import Server
from libs.constants import NodeType


@celery.task(name='node_synchronize')
def node_synchronize():
    from ec.node.model import Node
    old_masters = Node.query.filter(Node.type == NodeType.Master.value).all()
    old_master_data = {}
    for m in old_masters:
        old_master_data[m.server.ip] = m
    servers = Server.query.all()
    used_server = []
    for s in servers:
        if s.ip in used_server:
            continue
        used_server.append(s.ip)
        is_master = verify_devops(s.ip)

        if is_master:
            node_ips = get_nodes(s.ip)
            print(node_ips)
            used_server += node_ips
            old_master = Node.query.filter(Node.type == NodeType.Master.value).\
                filter(Node.server_id == s.id).first()
            if old_master:
                system_nodes = Server.query.filter(Server.ip.in_(node_ips)).all()
                node_ips = [node.ip for node in system_nodes]
                if sorted(node_ips) == sorted([node.server.ip for node in old_master.nodes]):
                    continue
                else:
                    for node in old_master.nodes:
                        node.delete()
                    old_master.delete()
                    master_id = Server.query.filter(Server.ip == s.ip).first().id
                    nodes = Server.query.filter(Server.ip.in_(node_ips)).all()
                    node_ids = [node.id for node in nodes]
                    version = get_devops_version(s.ip)
                    args = {'master_id': master_id, 'node_ids': node_ids,
                            'auto_create': False, 'version': version, 'status': 1}
                    Node.add(**args)
            else:
                master_id = Server.query.filter(Server.ip == s.ip).first().id
                nodes = Server.query.filter(Server.ip.in_(node_ips)).all()
                node_ids = [node.id for node in nodes]
                version = get_devops_version(s.ip)
                args = {'master_id': master_id, 'node_ids': node_ids,
                        'auto_create': False, 'version': version, 'status': 1}
                Node.add(**args)
        else:
            old_master = Node.query.filter(Node.type == NodeType.Master.value). \
                filter(Node.server_id == s.id).first()
            if old_master:
                old_master.delete()
                for node in old_master.nodes:
                    node.delete()


def verify_devops(ip):
    url = 'http://{}:5432'.format(ip)
    try:
        response = request('GET', url=url, timeout=2)
        return response.status_code == 200
    except Exception as e:
        return False


def get_devops_version(ip):
    url = 'http://{}:5432/api/v1/cluster/version'.format(ip)
    try:
        response = request('GET', url=url, timeout=2)
        if response.status_code == 200:
            return response.json().get('ReleaseVersion')
        else:
            return ''
    except Exception as e:
        return ''


def get_nodes(ip):
    url = 'http://{}:5432/api/v1/node?detail=1'.format(ip)
    node_ips = []
    try:
        response = request('GET', url, timeout=2)
        if response.status_code == 200:
            for key, value in response.json().items():
                node_ips.append(value.get('ipv4'))
    except Exception as e:
        print(e)

    return node_ips
