import datetime

import requests
from flask_mail import Message

from ec.account import User
from ec.project.model import Group, Project
from ec.bpmanage.models import ZipFile
from ec.deploy.model import Deploy, DeployTask
from ec.ext import db, celery, mail
from ec.server.model import Server
from libs.pb.deployment import ServicesStop, ServicesDeploy, DataDelete, ServicesDelete
from libs.constants import DevOps_Cookies
from ec.testcenter.models import CasesColTask


@celery.task
def execute_pipeline(pipeline_id):
    from ec.pipeline.model import Stage, Pipeline
    pipeline = Pipeline.find_by_id(pipeline_id)
    server = Server.find_by_id(pipeline.master.server_id)
    funcs = {
        0: stop_services,
        1: delete_services,
        2: delete_data,
        3: apply_services,
        4: deploy_services,
        5: execute_test
    }
    stages = Stage.query.filter(Stage.pipeline_id == pipeline_id).order_by(Stage.step).all()

    pipeline.start_at = datetime.datetime.now()
    pipeline.status = 1
    db.session.commit()
    status = 2
    for stage in stages:
        result = funcs.get(stage.type)(server, stage, pipeline.master_id)
        print(stage.type)
        print(result)
        if result != 0:
            status = 3
            break
    pipeline.status = status
    pipeline.end_at = datetime.datetime.now()
    db.session.commit()

    if status == 2:
        send_email(pipeline.start_at, '成功', pipeline.user_id)
    else:
        send_email(pipeline.start_at, '失败', pipeline.user_id)


def stop_services(server, stage, master_id=None):
    stop_server = stage.params.get('stop_server', False)
    stage.details = []
    if not stop_server:
        stage.start_at = datetime.datetime.now()
        stage.end_at = datetime.datetime.now()
        stage.details.append({"time": str(datetime.datetime.now())[:19], "msg":
            "【停止服务】：没有需要停止的服务"})
        db.session.commit()
        return 0
    extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
        'manager_host': server.ip,
        "kind": 1,
        "timeout": 300,
        "services": ""
    }
    stage.start_at = datetime.datetime.now()
    stage.status = 1
    stage.details.append({"time": str(datetime.datetime.now())[:19], "msg":
        "【停止服务】：开始执行停止服务"})
    db.session.commit()

    services_stop = ServicesStop(hosts=[server.ip], extra_vars=extra_vars)
    result = services_stop.run()
    stage.end_at = datetime.datetime.now()
    if result == 0:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【停止服务】：停止服务执行成功"})
        stage.status = 2
    else:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【停止服务】：停止服务执行失败"})
        stage.status = 3
    db.session.commit()
    return result


def delete_services(server, stage, master_id=None):
    services = stage.params.get('services', [])
    stage.details = []
    if len(services) == 0:
        stage.start_at = datetime.datetime.now()
        stage.end_at = datetime.datetime.now()
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【删除服务】：没有需要删除的服务"})
        db.session.commit()
        return 0
    extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
        'manager_host': server.ip,
        "kind": 3,
        "timeout": 300,
        "services": ','.join(services)
    }
    stage.start_at = datetime.datetime.now()
    stage.status = 1
    stage.details.append(
        {"time": str(datetime.datetime.now())[:19], "msg":
            "【删除服务】：开始执行删除服务"})
    db.session.commit()

    services_delete = ServicesDelete(hosts=[server.ip], extra_vars=extra_vars)
    result = services_delete.run()
    stage.end_at = datetime.datetime.now()
    if result == 0:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【删除服务】：删除服务成功"})
        stage.status = 2
    else:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【删除服务】：删除服务失败"})
        stage.status = 3
    db.session.commit()
    return result


def delete_data(server, stage, master_id=None):
    from ec.pipeline.model import Stage, Pipeline
    directory = stage.params.get('directory', [])
    stage.details = []
    if len(directory) == 0:
        stage.start_at = datetime.datetime.now()
        stage.end_at = datetime.datetime.now()
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【删除数据】：没有要删除的文件目录"})
        db.session.commit()
        return 0

    pipeline = Pipeline.find_by_id(stage.pipeline_id)
    master = pipeline.master

    stage.start_at = datetime.datetime.now()
    stage.status = 1
    stage.details.append(
        {"time": str(datetime.datetime.now())[:19], "msg":
            "【删除数据】：开始进行删除服务器数据"})
    db.session.commit()

    if master and master.nodes:
        for node in master.nodes:
            if node and node.server:
                extra_vars = {
                    'ansible_user': node.server.username,
                    'ansible_password': node.server.password,
                    'manager_host': node.server.ip,
                    'timeout': 1200,
                    "dirs": directory
                }

                node_data_delete = DataDelete(hosts=[node.server.ip], extra_vars=extra_vars)
                node_result = node_data_delete.run()
                if node_result == 0:
                    stage.details.append(
                        {"time": str(datetime.datetime.now())[:19], "msg":
                            "【删除数据】：删除Node{ip}目录 成功 - {dir}".format(ip=node.server.ip,
                                                                    dir=" , ".join(directory))})
                else:
                    stage.details.append(
                        {"time": str(datetime.datetime.now())[:19], "msg":
                            "【删除数据】：删除Node{ip}目录 失败 - {dir}".format(ip=node.server.ip,
                                                                    dir=" , ".join(directory))})

    extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
        'manager_host': server.ip,
        'timeout': 1200,
        "dirs": directory
    }

    data_delete = DataDelete(hosts=[server.ip], extra_vars=extra_vars)
    result = data_delete.run()
    stage.end_at = datetime.datetime.now()
    print(result)
    if result == 0:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【删除数据】：删除Master{ip}目录成功 - {dir}".format(ip=server.ip,
                                                         dir=" , ".join(directory))})
        stage.status = 2
    else:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【删除数据】：删除Master{ip}目录失败 - {dir}".format(ip=server.ip,
                                                         dir=" , ".join(directory))})
        stage.status = 3
    db.session.commit()
    return result


def apply_services(server, stage, master_id=None):
    project_ids = stage.params.get('project_ids', [])
    stage.details = []
    if len(project_ids) == 0:
        stage.start_at = datetime.datetime.now()
        stage.end_at = datetime.datetime.now()
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【依赖服务部署】：没有依赖服务需要部署"})
        db.session.commit()
        return 0

    result = 0
    stage.start_at = datetime.datetime.now()
    stage.status = 1
    stage.details.append(
        {"time": str(datetime.datetime.now())[:19], "msg":
            "【依赖服务部署】：开始进行依赖服务部署"})
    db.session.commit()

    for project_id in project_ids:
        deploys = Deploy.query.filter(Deploy.master_id == master_id). \
            filter(Deploy.project_id == project_id).all()
        project = Project.find_by_id(project_id)
        if not deploys:
            stage.details.append(
                {"time": str(datetime.datetime.now())[:19], "msg":
                    "【依赖服务部署】：获取{pro_name}-{pro_id}服务配置信息失败，未找到该数据".format(pro_name=project.name,
                                                                           pro_id=project_id
                                                                           )})
            result = 1
            break
        else:
            stage.details.append(
                {"time": str(datetime.datetime.now())[:19], "msg":
                    "【依赖服务部署】：获取{pro_name}-{pro_id}服务配置信息成功".format(pro_name=project.name,
                                                                    pro_id=project_id
                                                                    )})
        deploy_ids = [deploy.id for deploy in deploys]
        task = DeployTask.query.filter(DeployTask.deploy_id.in_(deploy_ids)). \
            order_by(DeployTask.created_at.desc()).first()

        if not task:
            result = 1
            break

        zip_obj = ZipFile.find_zip(id=task.file_id)
        zip_data, zip_name = zip_obj.data, zip_obj.fileName
        files = {
            'upload': (
                zip_name,
                zip_data,
                'application/zip'
            )
        }
        # filename = 'YL02202006-XXX-11-1234dj-dj-police_net-biz.biz-infra.1591704602440421105.yaml'
        # filepath = '/Users/yangshuyu/Downloads'
        # files = {
        #     ('upload', (filename, open(filepath + '/' + filename, 'rb'), 'application/octet-stream')),
        # }
        try:
            r = requests.post("http://{}:5432/api/v1/service/upload".format(server.ip), files=files,
                              cookies=DevOps_Cookies)
            services = r.json()["Snapshots"]
            stage.details.append(
                {"time": str(datetime.datetime.now())[:19], "msg":
                    "【依赖服务部署】：{pro_name}-{pro_id}编排上传服务器成功".format(pro_name=project.name,
                                                                   pro_id=project_id)})
        except Exception as e:
            stage.details.append(
                {"time": str(datetime.datetime.now())[:19], "msg":
                    "【依赖服务部署】：{pro_name}-{pro_id}编排上传服务器失败，失败原因-{e}".format(pro_name=project.name,
                                                                            pro_id=project_id,
                                                                            e=e)})
            break

        for s in services:
            url = "http://{}:5432/api/v1/service_snapshot/{}/apply".format(
                server.ip, s['name'])
            try:
                requests.post(url=url, cookies=DevOps_Cookies, timeout=20)
                stage.details.append(
                    {"time": str(datetime.datetime.now())[:19], "msg":
                        "【依赖服务部署】：服务器应用{pro_name}-{pro_id}编排文件成功".format(pro_name=project.name,
                                                                         pro_id=project_id
                                                                         )})
            except Exception as e:
                result = 1
                print(e)
                stage.details.append(
                    {"time": str(datetime.datetime.now())[:19], "msg":
                        "【依赖服务部署】：服务器应用{pro_name}-{pro_id}编排文件失败，失败原因-{e}".format(pro_name=project.name,
                                                                                  pro_id=project_id,
                                                                                  e=e)})

    stage.end_at = datetime.datetime.now()
    if result == 0:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【依赖服务部署】：所有依赖的项目部署成功"})
        stage.status = 2
    else:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【依赖服务部署】：存在依赖的项目部署失败问题"})
        stage.status = 3
    db.session.commit()
    return result


def has_pg_and_cloud_bridge(server):
    has_pg, has_cloud_bridge = False, False
    url = 'http://{}:5432/api/v1/service?detail=1'.format(server.ip)
    try:
        res = requests.get(url=url, cookies=DevOps_Cookies, timeout=2)
    except Exception as e:
        return False, False

    if res.status_code != 200:
        has_pg, has_cloud_bridge = False, False
    services = res.json()
    for service in services:
        if 'gpdb-gpdb' in service.get('name', ''):
            has_pg = True
            break

    for service in services:
        if 'cloud_bridge' in service.get('name', ''):
            has_cloud_bridge = True
        break

    return has_pg, has_cloud_bridge


def deploy_services(server, stage, master_id=None):
    from ec.pipeline.model import Stage, Pipeline

    # project_ids = stage.params.get('project_ids', [])
    pipeline = Pipeline.find_by_id(stage.pipeline_id)

    # group = Group.query.join(Project, Project.group_id == Group.id).filter(Project.id == pipeline.project_id).first()
    # stop_server_stage = Stage.query.filter(Stage.pipeline_id == stage.pipeline_id).filter(Stage.type == 0).first()
    # stop_server = stop_server_stage.params.get('stop_server', False)
    stage.details = []
    if pipeline.type == -1:
        stage.start_at = datetime.datetime.now()
        stage.end_at = datetime.datetime.now()
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【部署服务】：不执行部署任务"})
        db.session.commit()
        return 0

    try:
        clear_runonce(server=server, stage=stage)
    except Exception as e:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【部署服务】：清除Master机器服务的runonce出错，错误原因-{e}".format(e=e)})
        print(e)

    # if stop_server:
    #     services_map = {
    #         'vsr': 'core,vsr,cloud_bridge',
    #         'megcity': 'core,galaxy,cloud_bridge,megcity',
    #         'wisdom': 'gpdb,core,galaxy,cloud_bridge,wisdom',
    #         'insight': 'gpdb,core,galaxy,cloud_bridge,insight'
    #     }
    #     services = services_map.get(group.abbreviation, '')
    #
    # else:
    #     services = group.abbreviation
    #     services_list = services.split(',')
    #     sort_data = {
    #         'gpdb': 0,
    #         'core': 1,
    #         'galaxy': 2,
    #         'vsr': 3,
    #         'cloud_bridge': 4,
    #         'megcity': 5,
    #         'insight': 6,
    #         'wisdom': 7
    #     }
    #
    #     sorted_services_list = sorted(services_list, key=lambda item: sort_data.get(item, 100))
    #     services = ','.join(sorted_services_list)

    all_services = [
        'gpdb', 'core', 'galaxy', 'vsr', 'shenbu', 'iot',
        'cloud_bridge', 'megcity', 'insight', 'wisdom', 'kunlun',
        'viid', 'edge_server', 'mpsa', 'covid', 'wormhole', 'mpsa', 'gsp', 'gmp'
    ]

    services = ','.join(all_services)

    extra_vars = {
        'ansible_user': server.username,
        'ansible_password': server.password,
        'manager_host': server.ip,
        "kind": 2,
        "services": services,
        "timeout": stage.params.get('timeout', 300)
    }
    stage.start_at = datetime.datetime.now()
    stage.status = 1
    stage.details.append(
        {"time": str(datetime.datetime.now())[:19], "msg":
            "【部署服务】：开始执行部署服务"})
    db.session.commit()

    services_deploy = ServicesDeploy(hosts=[server.ip], extra_vars=extra_vars)
    result = services_deploy.run()
    stage.end_at = datetime.datetime.now()
    if result == 0:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
            "【部署服务】：服务部署成功"})
        stage.status = 2
    else:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
            "【部署服务】：服务部署失败"})
        stage.status = 3
    db.session.commit()
    return result


def execute_test(server, stage, master_id=None):
    test_data = stage.params
    whether_test = test_data.get('whether_test', False)

    if not whether_test:
        stage.start_at = datetime.datetime.now()
        stage.end_at = datetime.datetime.now()
        db.session.commit()
        return 0

    if test_data.get('interface_test_id'):
        CasesColTask.run_task(caseColTaskId=test_data.get('interface_test_id'))
    if test_data.get('scenes_test_id'):
        CasesColTask.run_api_scenario_tasks(scenarioTaskId=test_data.get('scenes_test_id'))
    stage.end_at = datetime.datetime.now()
    stage.status = 2
    db.session.commit()
    return 0


def clear_runonce(server, stage=None):
    services_list = []
    services = requests.get("http://" + server.ip + ":5432/api/v1/service",
                            cookies=DevOps_Cookies)
    if stage:
        stage.details.append(
            {"time": str(datetime.datetime.now())[:19], "msg":
                "【部署服务】：获取Master机器中所有的服务 成功"})

    for i in services.json():
        services_list.append(i['name'])

    for se in services_list:
        requests.post("http://" + server.ip + ":5432/api/v1/service/" + se + "/deploy_disable",
                      cookies=DevOps_Cookies, data={'names': ''})
        if stage:
            stage.details.append(
                {"time": str(datetime.datetime.now())[:19], "msg":
                    "【部署服务】：清除Master机器中{se}的runonce 成功".format(
                        se=se)})


def send_email(start_at, result, user_id):
    user = User.find_by_id(user_id)
    msg = Message(
        '任务执行完成提醒',
        recipients=[user.email]
        # recipients=['810043299@qq.com']
    )

    msg.html = '''
                             <html>
                     <head>任务执行完成提醒</head>
                     <body>
                     <p>在 {} 执行的任务执行完成<br>
                         执行结果: {}<br>
                         详情请去天狼效率中台查询: <a href="http://ec.cbg.megvii-inc.com/#/deploy/list-pipeline">详情</a>
                     </p>

                     </body>
                     </html>
                         '''. \
        format(
        start_at, result
    )

    mail.send(msg)
