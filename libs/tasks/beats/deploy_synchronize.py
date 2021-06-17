import datetime
import time

from sqlalchemy import and_, or_, func

from ec.deploy.model import Deploy, DeployTask
from ec.ext import celery, db
from ec.node.model import Node
from ec.project.model import Project
from libs.constants import DeployType, DeployMechanism, DeployTaskStatus
from sqlalchemy import extract
from libs.deployment.business_deployment import BusinessDeployment
from libs.redis import redis_client


@celery.task(name='deploy_synchronize')
def deploy_synchronize():
    project_sort = redis_client.get('project_sort')
    if project_sort:
        project_sort = eval(project_sort)
    else:
        project_sort = {}
    now = datetime.datetime.now()

    # 定时部署
    real_time_master_deploys = db.session.query(Deploy.master_id, func.array_agg(Deploy.id)). \
        join(Node, Node.id == Deploy.master_id). \
        filter(
        and_(
            Node.deleted_at.is_(None),
            Deploy.type == DeployType.Automatic.value,
            Deploy.mechanism == DeployMechanism.RealTime.value,
            extract('epoch', now - Deploy.last_time_at) >= Deploy.time_interval
        )
    ).group_by(Deploy.master_id).all()
    sort_real_time_deploys = {}

    for md in real_time_master_deploys:
        deploys = Deploy.query.filter(Deploy.id.in_(md[1])).all()
        for d in deploys:
            sort_real_time_deploys[d] = 100
            for key, value in project_sort.items():
                project = Project.find_by_id(d.project_id)
                if key in project.name:
                    sort_real_time_deploys[d] = value
                    continue

    last_real_time_deploys = sorted(sort_real_time_deploys.items(), key=lambda s: s[1])
    for d in last_real_time_deploys:
        rd = d[0]
        if int((now - rd.last_time_at).total_seconds()) < rd.time_interval:
            continue

        task = DeployTask.query.filter(DeployTask.deploy_id == rd.id). \
            order_by(DeployTask.created_at.desc()).first()

        if task and task.status == DeployTaskStatus.NotRunning.value and \
                int((now - rd.last_time_at).total_seconds()) > rd.time_interval:
            # 开始部署
            business_deploy.apply_async(args=[rd.id, task.id])
            time.sleep(5)

    # 实时部署
    timing_master_deploys = db.session.query(Deploy.master_id, func.array_agg(Deploy.id)). \
        join(Node, Node.id == Deploy.master_id). \
        filter(
        and_(
            Node.deleted_at.is_(None),
            Deploy.type == DeployType.Automatic.value,
            Deploy.mechanism == DeployMechanism.Timing.value,
        )
    ).group_by(Deploy.master_id).all()
    sort_timing_deploys = {}
    for md in timing_master_deploys:
        deploys = Deploy.query.filter(Deploy.id.in_(md[1])).all()
        for d in deploys:
            sort_real_time_deploys[d] = 100
            for key, value in project_sort.items():
                project = Project.find_by_id(d.project_id)
                if key in project.name:
                    sort_timing_deploys[d] = value
                    continue

    last_timing_deploys = sorted(sort_timing_deploys.items(), key=lambda s: s[1])

    for d in last_timing_deploys:
        td = d[0]
        if not now.day - td.last_time_at.day <= 0:
            continue

        if now >= datetime.datetime(
                now.year, now.month, now.day,
                int(td.time_point.split(':')[0]), int(td.time_point.split(':')[1])):
            task = DeployTask.query.filter(DeployTask.deploy_id == td.id). \
                order_by(DeployTask.created_at.desc()).first()

            if task and task.status == DeployTaskStatus.NotRunning.value:
                # 部署
                business_deploy.apply_async(args=[td.id, task.id])
                time.sleep(5)

    # real_time_deploys = Deploy.query.filter(
    #     and_(
    #         Deploy.type == DeployType.Automatic.value,
    #         Deploy.mechanism == DeployMechanism.RealTime.value,
    #         extract('epoch', now - Deploy.last_time_at) >= Deploy.time_interval
    #     )
    # ).all()
    #
    # for rd in real_time_deploys:
    #     if (now - rd.last_time_at).seconds < rd.time_interval:
    #         continue
    #
    #     task = DeployTask.query.filter(DeployTask.deploy_id == rd.id). \
    #         order_by(DeployTask.created_at.desc()).first()
    #
    #     if task and task.status == DeployTaskStatus.NotRunning.value and \
    #             (now - rd.last_time_at).seconds > rd.time_interval:
    #         # 开始部署
    #         business_deploy.apply_async(args=[rd.id, task.id])
    #
    # timing_deploys = Deploy.query.filter(
    #     and_(
    #         Deploy.type == DeployType.Automatic.value,
    #         Deploy.mechanism == DeployMechanism.Timing.value,
    #     )
    # ).all()
    #
    # for td in timing_deploys:
    #     if not now.day - td.last_time_at.day <= 0:
    #         continue
    #
    #     if now >= datetime.datetime(
    #             now.year, now.month, now.day,
    #             int(td.time_point.split(':')[0]), int(td.time_point.split(':')[1])):
    #         task = DeployTask.query.filter(DeployTask.deploy_id == td.id). \
    #             order_by(DeployTask.created_at.desc()).first()
    #
    #         if task and task.status == DeployTaskStatus.NotRunning.value:
    #             # 部署
    #             business_deploy.apply_async(args=[td.id, task.id])


@celery.task
def business_deploy(deploy_id, task_id):
    deploy = Deploy.find_by_id(deploy_id)
    task = DeployTask.find_by_id(task_id)
    try:
        bd = BusinessDeployment(deploy=deploy, task=task)
        servers = bd.upload_orch_file()
        metas, error = bd.apply_services(servers)
        if not error:
            bd.deploy_service(metas)
    except Exception as e:
        task.status = DeployTaskStatus.Failure.value
        task.end_at = datetime.datetime.now()
        db.session.commit()
        bd._send_deploy_email(result=False)
