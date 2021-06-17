import datetime

import requests

from ec.deploy.model import DeployTask
from ec.project.model import Group, Project
from ec.bpmanage.models import ZipFile
from ec.ext import db, celery, mail
from ec.server.model import Server
from libs.pb.deployment import ServicesDeploy, GspTest, GspGitPull
from libs.constants import DevOps_Cookies


@celery.task
def execute_gsp_test(gsp_result_id):
    from ec.gsp.result.model import GspResult
    gsp_result = GspResult.find_by_id(gsp_result_id)
    funcs = [repository_pull, deploy_service, gsp_test]

    status = 1
    gsp_result.status = status
    gsp_result.whether_stop = 0
    gsp_result.start_at = datetime.datetime.now().replace(tzinfo=None)
    gsp_result.end_at = None
    db.session.commit()

    status = 2  # 先默认成功
    for func in funcs:
        result = func(gsp_result_id)
        db.session.commit()
        if result == 10:
            status = 4
            break
        elif result != 0:
            status = 3
            break

    gsp_result = GspResult.find_by_id(gsp_result_id)
    gsp_result.status = status
    gsp_result.end_at = datetime.datetime.now().replace(tzinfo=None)
    db.session.commit()

    # if status == 2:
    #     send_email(pipeline.start_at, '成功', pipeline.user_id)
    # else:
    #     send_email(pipeline.start_at, '失败', pipeline.user_id)


def repository_pull(result_id):
    from ec.gsp.result.model import GspResult
    gsp_result = GspResult.find_by_id(result_id)

    if gsp_result.whether_stop == 1:
        return 10
    server = Server.query.filter(Server.ip == gsp_result.gsp_app_ip).first()
    branch = gsp_result.gsp_task.gitlab_branch

    if not server or not branch:
        return -1

    extra_vars = {
        'git_user': 'yangshuyu@megvii.com',
        'git_password': 'Ysy923619-',
        'version': branch,
        'ansible_user': server.username,
        'ansible_password': server.password,
    }

    ggp = GspGitPull([gsp_result.gsp_app_ip], extra_vars=extra_vars)
    result = ggp.run()
    return result


def deploy_service(result_id):
    from ec.gsp.result.model import GspResult
    gsp_result = GspResult.find_by_id(result_id)

    if gsp_result.whether_stop == 1:
        return 10

    deploy = gsp_result.deploy

    if not deploy:
        return 0

    deploy_task = DeployTask.query.filter(DeployTask.deploy_id == deploy.id).\
        order_by(DeployTask.created_at.desc()).first()

    if not deploy_task:
        return 0

    gsp_server = Server.query.filter(Server.ip == gsp_result.gsp_server_ip).first()
    project = Project.find_by_id(gsp_result.project_id)

    if not gsp_server or not project:
        return -1

    zip_obj = ZipFile.find_zip(id=deploy_task.file_id)
    zip_data, zip_name = zip_obj.data, zip_obj.fileName
    files = {
        'upload': (
            zip_name,
            zip_data,
            'application/zip'
        )
    }
    # filename = 'gsp-gsp110_rc0-SJ01202009-XXX-11-1234gsp-gsp-police_net-biz.biz-infra.1600769807617648784.yaml'
    # filepath = '/Users/yangshuyu/Downloads'
    # files = {
    #     ('upload', (filename, open(filepath + '/' + filename, 'rb'), 'application/octet-stream')),
    # }
    r = requests.post("http://{}:5432/api/v1/service/upload".format(gsp_result.gsp_server_ip), files=files,
                      cookies=DevOps_Cookies)
    services = r.json()["Snapshots"]

    for s in services:
        url = "http://{}:5432/api/v1/service_snapshot/{}/apply".format(
            gsp_result.gsp_server_ip, s['name'])
        try:
            requests.post(url=url, cookies=DevOps_Cookies, timeout=20)
        except Exception as e:
            print(e)
            return -1

    extra_vars = {
        'ansible_user': gsp_server.username,
        'ansible_password': gsp_server.password,
        'manager_host': gsp_server.ip,
        "kind": 2,
        "services": 'gsp',
        "timeout": 1200
    }
    services_deploy = ServicesDeploy(hosts=[gsp_server.ip], extra_vars=extra_vars)
    result = services_deploy.run()
    return result


def gsp_test(result_id):
    from ec.gsp.result.model import GspResult
    gsp_result = GspResult.find_by_id(result_id)
    if gsp_result.whether_stop == 1:
        return 10

    gsp_app_server = Server.query.filter(Server.ip == gsp_result.gsp_app_ip).first()
    old_envs = gsp_result.gsp_task.envs
    envs = 'export GSP_TEST=TRUE;'

    if old_envs:
        for index, old_env in enumerate(old_envs):
            # if index != 0:
            #     envs += ';'
            envs += 'export {}={};'.format(old_env.get('key'), old_env.get('value'))

    extra_vars = {
        'ansible_user': gsp_app_server.username,
        'ansible_password': gsp_app_server.password,
        'test_file': gsp_result.gsp_task.script,
        'result_id': gsp_result.id,
        'envs': envs,
        #
        #     {
        #     'server_endpoint': '10.122.100.179:23471',
        #     'access_key': 'admin',
        #     'secret_key': 'minioadmin'
        # },
    }
    print(envs)
    gt = GspTest([gsp_result.gsp_app_ip], extra_vars=extra_vars)
    result = gt.run()
    return result
