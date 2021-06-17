import datetime

from ec.deploy.model import Deploy, DeployTask
from ec.ext import celery, db
from libs.constants import DeployTaskStatus
from libs.deployment.business_deployment import BusinessDeployment


@celery.task
def manual_deploy(deploy_id):
    deploy = Deploy.find_by_id(deploy_id)
    task = DeployTask.query.filter(DeployTask.deploy_id == deploy_id).\
        order_by(DeployTask.created_at.desc()).first()
    if task and task.status == DeployTaskStatus.NotRunning.value:
        bd = BusinessDeployment(deploy=deploy, task=task)
        try:
            servers = bd.upload_orch_file()
            metas, error = bd.apply_services(servers)
            if error:
                return
            error = bd.deploy_service(metas)
            if error:
                return
        except Exception as e:
            task.status = DeployTaskStatus.Failure.value
            task.end_at = datetime.datetime.now()
            db.session.commit()
            bd._send_deploy_email(result=False)
