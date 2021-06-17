# -*- coding: utf-8 -*-
# Created by Duanwei on 2019/12/23

from ec.ext import celery
from ec.ci_cd.model import CIPipelines, CIProject
from libs.ci_util.gitlab_util import GitlabAPI
from libs.logging_log2 import get_logger

logger = get_logger(name="git_pipeline_info")


@celery.task(name="get_pipelines")
def get_pipelines():
    g = GitlabAPI()
    print("定时任务：每120秒执行一次\n")
    ci_gitlab_project_ids = CIProject.query.with_entities(
        CIProject.id, CIProject.gitlab_project_id, CIProject.branch_name
    )
    # 获取所有的ci proid,gitlab id,branchname
    all_record = ci_gitlab_project_ids.all()
    for record in all_record:
        ci_project_id = record[0]
        gitlab_id = record[1]
        branch_name = record[2]
        print(ci_project_id, gitlab_id, branch_name)
        latest_pipeline = (
            CIPipelines.query.filter(CIPipelines.ci_project_id == ci_project_id)
            .order_by(CIPipelines.updated_at.desc())
            .first()
        )
        if not latest_pipeline:
            latest_pipeline_id = 0
        else:
            latest_pipeline_id = latest_pipeline.pipeline_id
        project, pipelines = g.get_project_pipelines_by_project_id(
            projectid=gitlab_id, branchname=branch_name
        )
        print("**latest_pipeline_id**: " + str(latest_pipeline_id))
        if pipelines:
            for p in pipelines:
                args = {}
                pipeline_info = project.pipelines.get(p.id)
                if int(p.id) > int(latest_pipeline_id):
                    if (
                        pipeline_info.status == "pending"
                        or pipeline_info.status == "running"
                    ):
                        print("目前正在运行: %s" % str(pipeline_info.status))
                        continue
                    else:
                        args["ci_project_id"] = ci_project_id
                        args["pipeline_id"] = pipeline_info.id
                        args["pipeline_sha"] = pipeline_info.sha
                        args["pipeline_ref"] = pipeline_info.ref
                        args["pipeline_status"] = pipeline_info.status
                        args["pipeline_web_url"] = pipeline_info.web_url
                        if pipeline_info.user:
                            args["pipeline_user"] = pipeline_info.user["name"]
                        else:
                            args["pipeline_user"] = "无"
                        args["pipeline_created_at"] = pipeline_info.created_at
                        args["pipeline_updated_at"] = pipeline_info.updated_at
                        args["pipeline_finished_at"] = pipeline_info.finished_at
                        args["pipeline_duration"] = pipeline_info.duration
                        CIPipelines.add(**args)
                else:
                    print("已获取到最新记录！\n")
                    break
        else:
            print("无pipeline！")
            continue
