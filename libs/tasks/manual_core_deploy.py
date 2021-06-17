import datetime

from ec.core_deploy.model import CoreDeploy, CoreDeployTask, CoreDeployPg
from ec.ext import celery, db
from libs.deployment.core_deployment import CoreDeployment
from libs.deployment.pg_deployment import PgDeployment


@celery.task
def manual_core_deploy(deploy_id):
    deploy = CoreDeploy.find_by_id(deploy_id)
    task = CoreDeployTask.query.filter(CoreDeployTask.deploy_id == deploy_id).\
        order_by(CoreDeployTask.created_at.desc()).first()
    pg = CoreDeployPg.query.filter(CoreDeployPg.task_id == task.id).first()

    cd = CoreDeployment(deploy=deploy, task=task)
    cd.set_task_start_status()

    is_deploying = cd.check_whether_deploying()
    if not is_deploying:
        print('有服务正在部署')
        return

    if pg:
        pd = PgDeployment(deploy=deploy, pg=pg)
        pd_result = pd.deployment()
        if pd_result:
            cd_result = cd.deployment()
        else:
            cd.set_error_status()
    else:
        cd_result = cd.deployment()
